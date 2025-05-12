#crawler.py (크롤링: “+” 버튼 → 팝업 → 태그)

import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def fetch_tags_via_plus_button(app_id):
    """
    1) https://store.steampowered.com/app/{app_id}
    2) div.app_tag.add_button (+버튼) 클릭
    3) #app_tagging_modal a.app_tag 에서 태그 추출
    반환: {"app_id":..., "name":..., "user_tags":[...]}
    """
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # 디버깅 시 창 확인하려면 주석 처리
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    result = {
        "app_id": app_id,
        "name": None,
        "user_tags": []
    }

    try:
        # 페이지 접속
        url = f"https://store.steampowered.com/app/{app_id}"
        driver.get(url)
        time.sleep(1)

        # (A) 게임 이름
        try:
            name_elem = driver.find_element(By.CSS_SELECTOR, ".apphub_AppName")
            result["name"] = name_elem.text.strip()
        except:
            pass

        # (B) +버튼
        try:
            plus_btn = driver.find_element(By.CSS_SELECTOR, "div.app_tag.add_button")
            plus_btn.click()
            time.sleep(1)
        except:
            print(f"[WARN] +버튼 찾기 실패 for app_id={app_id}")
            return result

        # (C) 팝업 태그
        try:
            tag_elems = driver.find_elements(By.CSS_SELECTOR, "#app_tagging_modal a.app_tag")
            tags = [el.text.strip() for el in tag_elems if el.text.strip()]
            result["user_tags"] = tags
        except:
            print(f"[WARN] 태그 수집 실패 for app_id={app_id}")

    finally:
        driver.quit()

    return result
