import os
import time
import pymysql
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def get_connection():
    """
    .env에서 로드한 DB_HOST, DB_USER, DB_PW, DB_NAME을 이용해 pymysql 연결
    """
    DB_HOST = os.getenv("host")
    DB_USER = os.getenv("dbuser")
    DB_PW = os.getenv("password")
    DB_NAME = os.getenv("name")

    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PW,
        database=DB_NAME,
        charset="utf8mb4"
    )

def steam_manual_login(driver):
    """
    스토어 로그인 페이지로 이동 -> 사용자 수동 로그인
    """
    login_url = "https://store.steampowered.com/login/"
    driver.get(login_url)
    print("\n[안내] Steam 로그인 페이지가 열렸습니다.")
    print("브라우저에서 직접 아이디/비번/2차인증을 마친 뒤, 콘솔에 Enter를 눌러주세요.")
    input("로그인 완료 후 Enter...")

def get_game_title(driver, store_url, fallback_app_id):
    """
    해당 store_url에서 #appHubAppName 요소를 찾아 게임 제목을 반환
    실패 시 'Unknown Title'
    """
    try:
        driver.get(store_url)
        title_elem = WebDriverWait(driver, 12).until(
            EC.visibility_of_element_located((By.XPATH, '//*[@id="appHubAppName"]'))
        )
        return title_elem.text.strip()
    except Exception as e:
        print(f"    [WARN] RecAppID={fallback_app_id} 제목 로딩 실패 → {e}")
        return "Unknown Title"

def main():
    print("[INFO] 스크립트 시작합니다...")

    # (A) .env 로딩 (DB 접속정보 읽기)
    load_dotenv()

    # (B) TITLELIST에서 현재 유효한 app_id 목록 가져오기
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            sql = """
                SELECT DISTINCT app_id
                FROM TITLELIST
                WHERE end_date = '9999-12-31 00:00:00'
            """
            cur.execute(sql)
            rows = cur.fetchall()
        conn.close()

        if not rows:
            print("[ERROR] TITLELIST에서 app_id를 하나도 못 가져옴. 스크립트 종료.")
            return

        base_app_ids = [r[0] for r in rows]
        print(f"[INFO] DB에서 가져온 유효한 app_id 개수: {len(base_app_ids)}")

    except Exception as e:
        print("[ERROR] DB 쿼리 중 오류:", e)
        return

    # (C) Selenium 드라이버 (창 보이게)
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # 필요 시 주석 해제
    options.add_argument("--disable-gpu")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # (수동 로그인)
    steam_manual_login(driver)

    # (D) 크롤링
    output_data = []
    for idx, base_app_id in enumerate(base_app_ids, start=1):
        print(f"\n[INFO] ({idx}/{len(base_app_ids)}) BaseAppID={base_app_id} 크롤링 시작.")
        rec_url = f"https://store.steampowered.com/recommended/morelike/app/{base_app_id}/"
        try:
            driver.get(rec_url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, '//*[@id="released"]/div/a[@data-ds-appid]'))
            )
        except Exception as e:
            print(f"  [WARN] BaseAppID={base_app_id} 추천 페이지 로드 실패: {e}")
            continue

        collected_ids = set()
        attempts = 0
        max_attempts = 10

        # 최대 9개 수집
        while len(collected_ids) < 9 and attempts < max_attempts:
            if attempts > 0:
                driver.refresh()
                time.sleep(1)
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, '//*[@id="released"]/div/a[@data-ds-appid]'))
                )
            except Exception as e:
                print(f"    [WARN] BaseAppID={base_app_id} 새로고침 후 로드 실패: {e}")

            elements = driver.find_elements(By.XPATH, '//*[@id="released"]/div/a[@data-ds-appid]')
            for el in elements:
                raw_appid = el.get_attribute("data-ds-appid")
                if not raw_appid:
                    continue
                splitted = raw_appid.split()
                valid = [x for x in splitted if x.isdigit()]
                if valid:
                    collected_ids.add(valid[0])
                if len(collected_ids) >= 9:
                    break

            attempts += 1
            if len(collected_ids) < 9:
                print(f"    [INFO] BaseAppID={base_app_id} 시도 {attempts}회 → {len(collected_ids)}/9개, 재시도...")
                time.sleep(1)

        if len(collected_ids) < 9:
            print(f"  [WARN] BaseAppID={base_app_id} → 추천 게임 9개 확보 실패. 스킵.")
            continue

        # 추천 게임 상세페이지로 제목 가져오기
        for rec_id in collected_ids:
            store_url = f"https://store.steampowered.com/app/{rec_id}"
            rec_title = get_game_title(driver, store_url, rec_id)
            if rec_title == "Unknown Title":
                print(f"    [WARN] BaseAppID={base_app_id}의 RecAppID={rec_id} 제목 불러오기 실패. 스킵.")
                continue

            output_data.append((base_app_id, rec_id, rec_title))
            print(f"    [INFO] BaseAppID={base_app_id} → RecAppID={rec_id}, 제목='{rec_title}'")

    driver.quit()

    if not output_data:
        print("[INFO] 결과가 없습니다. 스크립트 종료.")
        return

    # (E) DB INSERT
    try:
        conn = get_connection()
        cur = conn.cursor()
        # SIMILAR_GAMES 테이블: (base_app_id, recommended_app_id)에 UNIQUE KEY
        insert_sql = """
            INSERT INTO SIMILAR_GAMES (base_app_id, recommended_app_id, recommended_title)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE recommended_title = VALUES(recommended_title)
        """
        for row_data in output_data:
            cur.execute(insert_sql, row_data)
            # rowcount=0이면 변경없음, 1이면 INSERT or UPDATE
            if cur.rowcount == 0:
                print(f" -> [No changes] base_app_id={row_data[0]}, recommended_app_id={row_data[1]}")
            else:
                print(f" -> [INSERT or UPDATE OK] base_app_id={row_data[0]}, recommended_app_id={row_data[1]}")

        conn.commit()
        cur.close()
        conn.close()
        print(f"[INFO] 총 {len(output_data)}건 처리 완료 (개별 INSERT/UPDATE).")
    except Exception as e:
        print("[ERROR] DB INSERT 중 오류:", e)

    print("[INFO] 스크립트 완료!")

if __name__ == "__main__":
    main()
