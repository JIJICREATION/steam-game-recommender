import os
import pymysql
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException

# ✅ .env 파일 로드 및 DB 연결 정보 불러오기
load_dotenv()
DB_HOST = os.getenv("host")
DB_USER = os.getenv("dbuser")
DB_PASSWORD = os.getenv("password")
DB_NAME = os.getenv("name")

# ✅ 크롤링할 대상 `base_app_id`
target_app_id = 1476000

# ✅ Selenium 크롬 드라이버 설정
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # GUI 없이 실행
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920x1080")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# ✅ ChromeDriver 실행
service = Service(log_path=os.devnull)
driver = webdriver.Chrome(service=service, options=options)

# ✅ 크롤링할 URL
url = f"https://store.steampowered.com/recommended/morelike/app/{target_app_id}/"

# ✅ 추천 게임 데이터 저장 (중복 방지)
game_data = set()

# ✅ 최대 10번 시도하여 9개 데이터 확보
max_attempts = 10
attempt = 0

while len(game_data) < 9 and attempt < max_attempts:
    driver.get(url)
    time.sleep(3)  # ✅ 페이지가 완전히 로드되도록 대기

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.XPATH, '//*[@id="released"]/div/a[@data-ds-appid]'))
        )
        print(f"[{target_app_id}] 추천 페이지 로드 성공")
        
        game_elements = driver.find_elements(By.XPATH, '//*[@id="released"]/div/a[@data-ds-appid]')

        for game in game_elements:
            rec_app_id = game.get_attribute("data-ds-appid")
            game_url = game.get_attribute("href")

            # ✅ 중복 체크 후 추가
            if rec_app_id in [data[1] for data in game_data]:
                continue

            # ✅ 개별 추천 게임 상세 페이지로 이동하여 제목 추출
            driver.get(game_url)
            try:
                game_title = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="appHubAppName"]'))
                ).text.strip()
            except:
                game_title = "Unknown Title"

            game_data.add((target_app_id, rec_app_id, game_title))

            # ✅ 9개 데이터 확보되면 즉시 종료
            if len(game_data) >= 9:
                break

            driver.get(url)  # 추천 페이지로 돌아가기
        
    except StaleElementReferenceException:
        print(f"[{target_app_id}] 요소가 변경됨, 다시 시도")
    
    attempt += 1

driver.quit()

# ✅ 만약 9개를 확보하지 못했다면, 크롤링 실패로 간주
if len(game_data) < 9:
    print(f"❌ [{target_app_id}] 9개 데이터를 확보하지 못함. 현재 개수: {len(game_data)}")
    exit()

print(f"✅ [{target_app_id}] 9개 데이터 확보 완료!")

# ✅ DB에 연결하여 기존 `1476000` 데이터 삭제 후 새 데이터 추가
try:
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        charset='utf8mb4'
    )
    cursor = conn.cursor()

    

    # ✅ Step 2: 새로운 1476000 데이터 삽입
    insert_query = """
    INSERT INTO SEE_ALL (base_app_id, recommended_app_id, recommended_title)
    VALUES (%s, %s, %s);
    """
    cursor.executemany(insert_query, list(game_data))  # ✅ 9개 확보 후 삽입
    conn.commit()
    print(f"✅ {target_app_id} 데이터 추가 완료!")

except Exception as e:
    print(f"❌ DB 적재 중 오류 발생:", e)

finally:
    cursor.close()
    conn.close()
