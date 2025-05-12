
"""
이 스크립트는 MariaDB(MySQL) 데이터베이스의 LIST_OF_MOBA_INDI 테이블에 저장된 Steam 게임의 app_id를 기반으로,
각 게임의 Steam 추천 페이지에서 추천된 게임 최대 9개의 app_id와 제목을 수집하여 데이터베이스의 SEE_ALL 테이블에 저장합니다.

주요 단계:
1. 환경변수에서 데이터베이스 연결 정보를 불러옴
2. 데이터베이스에서 모든 app_id를 조회
3. Selenium을 이용해 Steam 웹페이지에서 추천 게임 데이터를 수집
 (see_all -> SIMILAR_GAMES 으로 변경)
"""










import os
import pymysql
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

# .env 파일 로드 및 DB 연결 정보 불러오기
load_dotenv()
DB_HOST = os.getenv("host")
DB_USER = os.getenv("dbuser")
DB_PASSWORD = os.getenv("password")
DB_NAME = os.getenv("name")

# DB에서 LIST_OF_MOBA_INDI 테이블의 app_id 가져오기 (모든 app_id 사용)
try:
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        charset='utf8mb4'
    )
    cursor = conn.cursor()
    cursor.execute("SELECT app_id FROM LIST_OF_MOBA_INDI")
    base_app_ids = cursor.fetchall()  # [(app_id,), (app_id,), ...]
    cursor.close()
    conn.close()
    if not base_app_ids:
        raise Exception("DB에서 APP_ID를 가져오지 못했습니다.")
except Exception as e:
    print("DB 연결 혹은 쿼리 실행 중 오류 발생:", e)
    exit()

# Selenium 크롬 드라이버 설정 (headless 모드)
options = webdriver.ChromeOptions()
options.add_argument("--headless")          # 창 없이 실행
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920x1080")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
# ChromeDriver 로그 억제 (Selenium 4 방식)
service = Service(log_path=os.devnull)
driver = webdriver.Chrome(service=service, options=options)

output_data = []  # 최종 결과 저장 리스트 (컬럼: base_app_id, recommended_app_id, recommended_title)

# 각 DB의 app_id마다 Steam 추천 페이지에서 추천 게임 9종 정보 추출
for base_app_id_tuple in base_app_ids:
    base_app_id = base_app_id_tuple[0]
    url = f"https://store.steampowered.com/recommended/morelike/app/{base_app_id}/"
    driver.get(url)
    
    # 페이지가 완전히 로드될 때까지 대기
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, '//*[@id="released"]/div/a[@data-ds-appid]'))
        )
    except Exception as e:
        print(f"[{base_app_id}] 추천 페이지 로드 실패:", e)
        continue
    
    # 추천 게임 목록에서 9개 데이터 수집 (최대 10회 시도)
    game_data = []
    attempt = 0
    max_attempts = 10
    while len(game_data) < 9 and attempt < max_attempts:
        driver.refresh()
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, '//*[@id="released"]/div/a[@data-ds-appid]'))
            )
        except Exception as e:
            print(f"[{base_app_id}] 새로고침 후 페이지 로딩 실패:", e)
        game_elements = driver.find_elements(By.XPATH, '//*[@id="released"]/div/a[@data-ds-appid]')
        game_data = [(game.get_attribute("data-ds-appid"), game.get_attribute("href"))
                     for game in game_elements[:9]]
        if len(game_data) < 9:
            print(f"[{base_app_id}] 시도 {attempt+1}회: 9개 미만의 게임 데이터 발견, 재시도 중...")
            time.sleep(2)
        attempt += 1
    
    if len(game_data) < 9:
        print(f"[{base_app_id}] 추천 게임 데이터 수집에 실패했습니다. 다음 APP_ID로 넘어갑니다.")
        continue
    
    # 각 추천 게임에 대해 게임 제목 추출 (실패 시 "Unknown Title" 처리)
    final_game_data = []
    for rec_app_id, game_url in game_data:
        driver.get(game_url)
        try:
            game_title = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="appHubAppName"]'))
            ).text.strip()
        except Exception as e:
            print(f"게임 제목 로딩 실패 for app_id {rec_app_id}: {e}")
            game_title = "Unknown Title"
        final_game_data.append((rec_app_id, game_title))
        driver.get(url)  # 추천 페이지로 돌아가기
    
    for rec_app_id, game_title in final_game_data:
        output_data.append((base_app_id, rec_app_id, game_title))

driver.quit()

# DB에 데이터 적재 (테이블 SEE_ALL 생성 후 데이터 삽입)
try:
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        charset='utf8mb4'
    )
    cursor = conn.cursor()
    create_table_query = """
    CREATE TABLE IF NOT EXISTS SEE_ALL (
        id INT AUTO_INCREMENT PRIMARY KEY,
        base_app_id BIGINT NOT NULL,
        recommended_app_id BIGINT NOT NULL,
        recommended_title VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL
    );
    """
    cursor.execute(create_table_query)
    conn.commit()
    
    insert_query = """
    INSERT INTO SEE_ALL (base_app_id, recommended_app_id, recommended_title)
    VALUES (%s, %s, %s)
    """
    cursor.executemany(insert_query, output_data)
    conn.commit()
    cursor.close()
    conn.close()
    print("DB에 데이터 적재 완료")
except Exception as e:
    print("DB 적재 중 오류 발생:", e)
