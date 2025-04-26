import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
from openai import OpenAI
import json
from dotenv import load_dotenv
import os

def get_contact_info_from_gpt(seller_info_text):
    """GPTを使用してセラー情報からメールアドレスと会社URLを抽出"""
    try:
        # デバッグ出力を詳細にする
        api_key = os.environ.get("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError("OpenAI APIキーが設定されていません")
        
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは優秀なアシスタントです。与えられたテキスト情報を参考に、連絡可能なメールアドレスと会社のURLを出力してください。"},
                {"role": "user", "content": f"以下のテキスト情報を参考に、連絡可能なメールアドレスと会社のURLを出力してください。このテキストには含まれていないため、GPT内にある情報を参考に出力してください。\n\n{seller_info_text}"}
            ],
            temperature=0.3
        )
        
        result = response.choices[0].message.content
        print(result)
        # メールアドレスとURLを抽出
        email = get_email_from_text(result)
        company_url = get_url_from_text(result)
        print(email, company_url)

        return [email, company_url]
    except Exception as e:
        print(f"GPT APIエラー: {e}")
        return ""

def remove_duplicate_company(df):
    # メールアドレス列で重複を削除（最初の出現を保持）
    df_cleaned = df.drop_duplicates(subset=['ブランド'], keep='first')
    
    print(f"重複削除前の行数: {len(df)}")
    print(f"重複削除後の行数: {len(df_cleaned)}")
    print(f"削除された重複行数: {len(df) - len(df_cleaned)}")
    print("--------------------------------")
    
    return df_cleaned

def remove_other_jp(df):
    df_cleaned = df[df['セラー所在地'] == 'JP']
    print(f"日本の行数: {len(df_cleaned)}")
    print(f"日本以外の行数: {len(df) - len(df_cleaned)}")
    print("--------------------------------")
    return df_cleaned

def get_element_text(element, xpath, default=""):
    """要素のテキストを安全に取得"""
    try:
        return element.find_element(By.XPATH, xpath).text
    except Exception:
        return default
    
def get_email_from_text(text):
    """テキストからメールアドレスを抽出"""
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    email_matches = re.findall(email_pattern, text)
    return email_matches[0] if email_matches else ""

def get_url_from_text(text):
    """テキストからURLを抽出"""
    url_pattern = r'https?://(?:[a-zA-Z0-9\-._~:/?#\[\]@!$&\'()*+,;=%])+'
    url_matches = re.findall(url_pattern, text)
    return url_matches[0] if url_matches else ""

def get_seller_info(driver, seller_url):
    """販売者情報の取得"""
    seller_info = {
        "seller_name": "",
        "seller_info_link": "",
        "store_evaluation": "",
        "company_about": "",
        "company_name": "",
        "company_tell": "",
        "company_address": "",
        "company_email": "",
        "company_url": ""
    }
    
    try:
        # 販売者ページを開く
        driver.get(seller_url)
        time.sleep(3)  # ページ読み込み待機
        
        # 販売者情報の取得
        seller_info["company_about"] = get_element_text(driver, "(//*[@id='spp-expander-about-seller']/div[1]/div[2] | //*[@id='spp-expander-about-seller']/div)[last()]")
        seller_info["store_evaluation"] = get_element_text(
            driver, '//*[@id="seller-info-feedback-summary"]/span/a')
        
        store_info = driver.find_element(By.XPATH, '//*[@id="page-section-detail-seller-info"]/div/div/div')
        seller_info["company_name"] = get_element_text(store_info, './/div[2]/span[2]')
        seller_info["company_tell"] = get_element_text(store_info, './/div[3]/span[2]')
        
        # 住所情報の取得
        address_blocks = store_info.find_elements(By.XPATH, './/div[contains(@class, "indent-left")]')
        address_parts = []
        for block in address_blocks:
            address_part = get_element_text(block, './/span')
            if address_part:
                address_parts.append(address_part)
        seller_info["company_address"] = ",".join(address_parts)
        
        # メールアドレスの抽出
        seller_info["company_email"] = get_email_from_text(seller_info["company_about"])

        # URLの抽出
        seller_info["company_url"] = get_url_from_text(seller_info["company_about"])

    except Exception as e:
        print(f"エラーが発生しました: {e}")
    
    return seller_info

def scrape_seller_info(df):
    out_df = pd.DataFrame(columns=list(df.columns) + ['会社名', '会社電話番号', '会社住所', '会社評価', '会社概要', 'メールアドレス', '会社URL'])
    
    # Chromeドライバのセットアップ
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    df = remove_duplicate_company(df)
    df = remove_other_jp(df)
    df.reset_index(drop=True, inplace=True)
    
    for index, row in df.iterrows():
        seller_url = row['セラーリンク']
        if pd.isna(seller_url):  # セラーリンクが存在しない場合はスキップ
            continue
            
        try:
            print(f"\r処理中: {index + 1}/{len(df)}", end="")
            
            # 販売者情報の取得
            seller_info = get_seller_info(driver, seller_url)
            # if seller_info["company_email"] == "" or seller_info["company_url"] == "":
            #     gpt_result = get_contact_info_from_gpt(row["セラー情報"])

            # if seller_info["company_email"] == "":
            #     seller_info["company_email"] = gpt_result[0]
            # if seller_info["company_url"] == "":
            #     seller_info["company_url"] = gpt_result[1]
            
            # 元のデータフレームに新しい情報を追加
            out_df.loc[index] = df.loc[index].tolist() + [
                seller_info["company_name"],
                seller_info["company_tell"],
                seller_info["company_address"],
                seller_info["store_evaluation"],
                seller_info["company_about"],
                seller_info["company_email"],
                seller_info["company_url"]
            ]
            
            # 進捗を保存
            out_df.to_csv('towel_updated.csv', index=False, encoding='utf-8-sig')
            
        except Exception as e:
            print(f"\nエラーが発生しました: {e}")
            continue
    
    driver.quit()
    print("\nスクレイピング完了！ CSVファイルに保存しました。")

if __name__ == "__main__":
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(env_path)
    print(f".envファイルの読み込み状態: {os.path.exists(env_path)}")

    df = pd.read_csv('./csv/towel.csv')
    scrape_seller_info(df)
