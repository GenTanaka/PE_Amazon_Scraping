import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 定数定義
SEARCH_KEYWORD = "ねんど"
MAX_PRODUCTS_PER_PAGE = 100
PAGE_LOAD_WAIT = 3
OUTPUT_FILE = "amazon_ec_consult_list.csv"
MAX_PAGES = 1

def setup_chrome_driver():
    """Chromeドライバーの設定とインスタンス化"""
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver_dir = os.path.dirname(ChromeDriverManager().install())
    chromedriver_path = os.path.join(driver_dir, "chromedriver")
    os.chmod(chromedriver_path, 0o755)
    
    return webdriver.Chrome(service=Service(chromedriver_path), options=options)

def get_element_text(element, xpath, default=""):
    """要素のテキストを安全に取得"""
    try:
        return element.find_element(By.XPATH, xpath).text
    except Exception:
        return default

def get_element_attribute(element, xpath, attribute, default=""):
    """要素の属性を安全に取得"""
    try:
        return element.find_element(By.XPATH, xpath).get_attribute(attribute)
    except Exception:
        return default

def extract_asin(driver):
    """ASIN情報の抽出"""
    try:
        # 商品詳細からASINを探す
        for xpath in [
            '//*[@id="productDetails_detailBullets_sections1"]/tbody/tr',
            '//*[@id="productDetails_techSpec_section_1"]/tbody/tr',
            '//*[@id="detailBullets_feature_div"]/ul/li'
        ]:
            elements = driver.find_elements(By.XPATH, xpath)
            for element in elements:
                if xpath.endswith('li'):
                    if "ASIN" in element.find_element(By.XPATH, './/span/span[1]').text:
                        return element.find_element(By.XPATH, './/span/span[2]').text
                else:
                    if "ASIN" in element.find_element(By.XPATH, './/th').text:
                        return element.find_element(By.XPATH, './/td').text
        return ""
    except Exception:
        return ""

def get_seller_info(driver):
    """販売者情報の取得"""
    seller_info = {
        "seller_name": "",
        "seller_info_link": "",
        "store_evaluation": "",
        "company_name": "",
        "company_tell": "",
        "company_address": ""
    }
    
    try:
        seller_element = driver.find_element(By.XPATH, '//a[@id="sellerProfileTriggerId"]')
        seller_info["seller_name"] = seller_element.text
        
        # Amazon.co.jpの場合の特別処理
        if seller_info["seller_name"] == "Amazon.co.jp":
            return {
                "seller_name": "Amazon.co.jp",
                "seller_info_link": "Amazon.co.jpのため取得不可",
                "store_evaluation": "Amazon.co.jpのため取得不可",
                "company_name": "",
                "company_tell": "Amazon.co.jpのため取得不可",
                "company_address": "Amazon.co.jpのため取得不可"
            }
        
        # 販売者ページを開く
        seller_info["seller_info_link"] = seller_element.get_attribute("href")
        driver.execute_script("window.open(arguments[0]);", seller_info["seller_info_link"])
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(PAGE_LOAD_WAIT)
        
        # 販売者情報の取得
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
        
        driver.close()
        driver.switch_to.window(driver.window_handles[-1])
        
    except Exception:
        try:
            seller_element = driver.find_element(By.XPATH, '//*[@id="merchantInfoFeature_feature_div"]/div[2]/div[1]/span/a')
            seller_info["seller_name"] = seller_element.text

            if seller_info["seller_name"] == "Amazon.co.jp":
                return {
                    "seller_name": "Amazon.co.jp",
                    "seller_info_link": "Amazon.co.jpのため取得不可",
                    "store_evaluation": "Amazon.co.jpのため取得不可",
                    "company_name": "",
                    "company_tell": "Amazon.co.jpのため取得不可",
                    "company_address": "Amazon.co.jpのため取得不可"
                }
        except Exception:
            pass
    
    print(seller_info["seller_name"])
    return seller_info

def scrape_product_info(driver, product):
    """商品情報のスクレイピング"""
    product_info = {
        "product_title": get_element_text(product, './/h2/span'),
        "product_link": get_element_attribute(product, './/a', "href")
    }
    
    if not product_info["product_link"]:
        return None
    
    # 商品ページを開く
    driver.execute_script("window.open(arguments[0]);", product_info["product_link"])
    driver.switch_to.window(driver.window_handles[-1])
    time.sleep(PAGE_LOAD_WAIT)
    
    # 基本情報の取得
    product_info.update({
        "price": get_element_text(driver, '//span[@class="a-price-whole"]'),
        "seller_name": get_element_text(driver, '//a[@id="bylineInfo"]').replace("のストアを表示","").replace("ブランド: ",""),
        "review_count": get_element_text(driver, '//span[@id="acrCustomerReviewText"]').replace("個の評価","").replace(",",""),
        "asin": extract_asin(driver),
        "bought_count": get_element_text(driver, '//*[@id="social-proofing-faceout-title-tk_bought"]'),
    })
    
    # タグ情報の取得
    try:
        tag_element = driver.find_element(By.XPATH, '//*[@id="acBadge_feature_div" or @id="zeitgeistBadge_feature_div"]/div')
        if tag_element.get_attribute("class") == "zg-badge-wrapper":
            product_info["tag"] = tag_element.find_element(By.XPATH, './/a/i').text.replace("\n","")
        else:
            product_info["tag"] = tag_element.text.replace("\n","")
    except Exception:
        product_info["tag"] = ""
    
    # 販売者情報の取得
    seller_info = get_seller_info(driver)
    product_info.update(seller_info)
    
    driver.close()
    driver.switch_to.window(driver.window_handles[0])
    
    return product_info

def main():
    driver = setup_chrome_driver()
    url = f"https://www.amazon.co.jp/s?k={SEARCH_KEYWORD}"
    driver.get(url)
    
    results = []
    page = 0
    
    try:
        while True:
            page += 1
            print(f"Processing page: {page}")
            time.sleep(PAGE_LOAD_WAIT)
            
            products = driver.find_elements(By.XPATH, '//div[@data-component-type="s-search-result"]')
            for i, product in enumerate(products, 1):
                product_info = scrape_product_info(driver, product)
                if product_info:
                    results.append({
                        "商品タイトル": product_info["product_title"],
                        "ブランド名": product_info["seller_name"],
                        "商品URL": product_info["product_link"],
                        "金額": product_info["price"],
                        "購入者数": product_info["bought_count"],
                        "ASIN": product_info["asin"],
                        "タグ": product_info["tag"],
                        "レビュー数": product_info["review_count"],
                        "会社評価": product_info["store_evaluation"],
                        "会社ページ": product_info["seller_info_link"],
                        "会社名": product_info["company_name"],
                        "会社電話番号": product_info["company_tell"],
                        "会社住所": product_info["company_address"],
                    })
                
                if i >= MAX_PRODUCTS_PER_PAGE:
                    break
            
            if page >= MAX_PAGES:
                break
            try:
                next_page = driver.find_element(By.XPATH, '//div[@role="navigation"]/span/ul/li[last()]/span/a')
                next_page.click()
            except Exception:
                print("次ページが見つかりませんでした。")
                break
        
        # 結果をCSVに保存
        df = pd.DataFrame(results)
        df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
        print("スクレイピング完了！ CSVファイルに保存しました。")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
