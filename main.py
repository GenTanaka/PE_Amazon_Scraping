import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Chromeドライバのセットアップ
options = webdriver.ChromeOptions()
# ヘッドレスモードで実行する場合は以下のコメントを外す
# options.add_argument('--headless')

# webdriver_manager で取得したパスから実行可能なchromedriverのパスを指定する
driver_dir = os.path.dirname(ChromeDriverManager().install())
chromedriver_path = os.path.join(driver_dir, "chromedriver")
# 実行権限が付与されているか確認（必要なら chmod で権限変更）
os.chmod(chromedriver_path, 0o755)

driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)

# 例として「老舗」をキーワードにAmazon検索（Amazon.co.jp）を実施
search_keyword = "ねんど"
url = f"https://www.amazon.co.jp/s?k={search_keyword}"
driver.get(url)

# 以下、既存のスクレイピング処理（例）
results = []
page = 0
while True:
    page += 1
    time.sleep(3)  # ページ読み込み待ち 
    print(f"Processing page: {page}")
    products = driver.find_elements(By.XPATH, '//div[@data-component-type="s-search-result"]')
    
    for product in products:
        try:
            product_title = product.find_element(By.XPATH, './/h2/span').text
            print(product_title)
        except Exception:
            product_title = ""
        
        try:
            product_link = product.find_element(By.XPATH, './/a').get_attribute("href")
        except Exception:
            continue
        
        driver.execute_script("window.open(arguments[0]);", product_link)
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(3)
        
        try:
            seller_name = driver.find_element(By.XPATH, '//a[@id="bylineInfo"]').text
            seller_name = seller_name.replace("のストアを表示","").replace("ブランド: ","")
        except Exception:
            seller_name = ""
        
        try:
            review_text = driver.find_element(By.XPATH, '//span[@id="acrCustomerReviewText"]').text
            review_text = review_text.replace("個の評価","").replace(",","")
        except Exception:
            review_text = ""
        
        try:
            seller_info_link = driver.find_element(By.XPATH, '//a[@id="bylineInfo"]').get_attribute("href")
            driver.execute_script("window.open(arguments[0]);", seller_info_link)
            driver.switch_to.window(driver.window_handles[-1])
            time.sleep(3)
            
            try:
                selling_category = driver.find_element(By.XPATH, '//*[@id="sellerCategories"]').text
            except Exception:
                selling_category = ""
            try:
                location = driver.find_element(By.XPATH, '//*[@id="sellerLocation"]').text
            except Exception:
                location = ""
            try:
                sales = driver.find_element(By.XPATH, '//*[@id="sellerSales"]').text
            except Exception:
                sales = ""
            
            driver.close()
            driver.switch_to.window(driver.window_handles[-1])
        except Exception:
            selling_category = ""
            location = ""
            sales = ""
        
        results.append({
            "商品タイトル": product_title,
            "会社名（販売者）": seller_name,
            "会社ページ": seller_info_link,
            "出品カテゴリ": selling_category,
            "所在地": location,
            "レビュー数": review_text,
            "売上情報": sales
        })
        
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        # break
    
    try:
        next_page = driver.find_element(By.XPATH, '//div[@role="navigation"]/span/ul/li[last()]/span/a')
        next_page.click()
        break
    except Exception:
        print("次ページが見つかりませんでした。")
        break

df = pd.DataFrame(results)
df.to_csv("amazon_ec_consult_list.csv", index=False, encoding="utf-8-sig")
print("スクレイピング完了！ CSVファイルに保存しました。")

driver.quit()
