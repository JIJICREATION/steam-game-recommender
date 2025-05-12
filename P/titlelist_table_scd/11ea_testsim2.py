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
    login_url = "https://store.steampowered.com/login/"
    driver.get(login_url)
    print("\n[안내] Steam 로그인 페이지가 열렸습니다.")
    print("브라우저에서 직접 아이디/비번/2차인증을 마친 뒤, 콘솔에 Enter를 눌러주세요.")
    input("로그인 완료 후 Enter...")

def get_game_title(driver, store_url, fallback_app_id):
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

    load_dotenv()

    # 1) TITLELIST에서 app_id 가져오기
    base_app_ids = []
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

        # rows -> [(63200,), (570,), ...]
        base_app_ids = [r[0] for r in rows]
        print(f"[INFO] DB에서 가져온 유효한 app_id 개수: {len(base_app_ids)}")

    except Exception as e:
        print("[ERROR] DB 쿼리 중 오류:", e)
        return

    # (★) 여기서 상위 10개만 사용
    if len(base_app_ids) > 11:
        base_app_ids = base_app_ids[:11]
    print(f"[INFO] 이번 테스트는 최대 10개만 크롤합니다. 실제 사용 app_id 개수: {len(base_app_ids)}")

    # 2) Selenium 드라이버 (창 보이게)
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # 필요시
    options.add_argument("--disable-gpu")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    steam_manual_login(driver)

    # 3) 크롤링
    output_data = []
    for idx, base_app_id in enumerate(base_app_ids, start=1):
        print(f"\n[INFO] ({idx}/{len(base_app_ids)}) base_app_id={base_app_id} 처리 중...")
        morelike_url = f"https://store.steampowered.com/recommended/morelike/app/{base_app_id}/"

        try:
            driver.get(morelike_url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, '//*[@id="released"]/div/a[@data-ds-appid]'))
            )
        except Exception as e:
            print(f"  [WARN] BaseAppID={base_app_id}, morelike 페이지 로딩 실패: {e}")
            continue

        collected_ids = set()
        attempts = 0
        max_attempts = 10

        while len(collected_ids) < 9 and attempts < max_attempts:
            if attempts > 0:
                driver.refresh()
                time.sleep(1)
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, '//*[@id="released"]/div/a[@data-ds-appid]'))
                )
            except:
                pass

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
                print(f"    [INFO] {len(collected_ids)}/9개 - 재시도 ({attempts})")
                time.sleep(1)

        if len(collected_ids) < 9:
            print(f"  [WARN] base_app_id={base_app_id}: 9개 미만, 스킵.")
            continue

        for rec_id in collected_ids:
            store_url = f"https://store.steampowered.com/app/{rec_id}"
            rec_title = get_game_title(driver, store_url, rec_id)
            if rec_title == "Unknown Title":
                print(f"    [WARN] base_app_id={base_app_id}, recommended_app_id={rec_id} -> 제목 로딩 실패, 스킵.")
                continue

            output_data.append((base_app_id, rec_id, rec_title))
            print(f"    [INFO] base_app_id={base_app_id} -> recommended_app_id={rec_id}, title='{rec_title}'")

    driver.quit()

    if not output_data:
        print("[INFO] 크롤링된 데이터가 없습니다. 종료.")
        return

    # 4) DB INSERT (TEST_SIMILAR_GAMES 예시)
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS TEST_SIMILAR_GAMES (
        id INT AUTO_INCREMENT PRIMARY KEY,
        base_app_id BIGINT NOT NULL,
        recommended_app_id BIGINT NOT NULL,
        recommended_title VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
        user_tags TEXT DEFAULT NULL,
        UNIQUE KEY idx_unique_appid (base_app_id, recommended_app_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci
    """

    insert_sql = """
    INSERT INTO TEST_SIMILAR_GAMES (base_app_id, recommended_app_id, recommended_title)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE
        recommended_title = VALUES(recommended_title)
    """

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(create_table_sql)
            conn.commit()

            for row_data in output_data:
                cur.execute(insert_sql, row_data)
                if cur.rowcount == 0:
                    print(f" -> [No changes] {row_data[0]}-{row_data[1]}")
                else:
                    print(f" -> [INSERT or UPDATE OK] {row_data[0]}-{row_data[1]}")

        conn.commit()
        conn.close()
        print(f"[INFO] 총 {len(output_data)}건 처리 완료 (TEST_SIMILAR_GAMES).")
    except Exception as e:
        print("[ERROR] DB 처리 중 오류:", e)

    print("[INFO] 스크립트 완료!")


if __name__ == "__main__":
    main()
