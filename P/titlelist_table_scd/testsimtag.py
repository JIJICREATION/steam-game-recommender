import os
import time
import json
import pymysql
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

################################################
# 1) DB 연결 & 환경
################################################
def get_connection():
    load_dotenv()
    dbuser = os.getenv('dbuser')
    password = os.getenv('password')
    host = os.getenv('host')
    port = int(os.getenv('port', 3306))
    dbname = os.getenv('name')

    return pymysql.connect(
        host=host,
        user=dbuser,
        password=password,
        db=dbname,
        port=port,
        charset="utf8mb4"
    )

def ensure_user_tags_column_in_test_table():
    """
    TEST_SIMILAR_GAMES 테이블에 user_tags 컬럼이 없으면 JSON 타입으로 추가.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
            ALTER TABLE TEST_SIMILAR_GAMES
                ADD COLUMN IF NOT EXISTS user_tags JSON NULL
            """
            try:
                cur.execute(sql)
                conn.commit()
            except pymysql.err.OperationalError as e:
                print(f"[INFO] user_tags 컬럼 추가 중(혹은 이미 존재) => {e}")
    finally:
        conn.close()

################################################
# 2) TEST_SIMILAR_GAMES 접근 함수
################################################
def fetch_all_test_similar_rows():
    """
    TEST_SIMILAR_GAMES 테이블에서 (id, base_app_id, recommended_app_id) 전부 가져오기
    """
    conn = get_connection()
    rows = []
    try:
        with conn.cursor() as cur:
            sql = "SELECT id, base_app_id, recommended_app_id FROM TEST_SIMILAR_GAMES"
            cur.execute(sql)
            rows = cur.fetchall()
    finally:
        conn.close()
    return rows

def get_current_user_tags_in_db(row_id):
    """
    DB에서 해당 row_id의 user_tags(JSON)를 읽어 파이썬 리스트로 반환
    (이때 리스트 안의 값들은 정수 ID 목록으로 가정)
    """
    conn = get_connection()
    user_tags_json = None
    try:
        with conn.cursor() as cur:
            sel_sql = "SELECT user_tags FROM TEST_SIMILAR_GAMES WHERE id=%s"
            cur.execute(sel_sql, (row_id,))
            row = cur.fetchone()
            if row:
                user_tags_json = row[0]
    finally:
        conn.close()

    if not user_tags_json:
        return []
    try:
        return json.loads(user_tags_json)  # ex: [1,3,5]
    except:
        return []

def update_user_tags_in_test_table(row_id, tags_json):
    """
    row_id 행의 user_tags 컬럼을 tags_json(문자열)으로 UPDATE
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
            UPDATE TEST_SIMILAR_GAMES
               SET user_tags = %s
             WHERE id = %s
            """
            cur.execute(sql, (tags_json, row_id))
        conn.commit()
    finally:
        conn.close()

################################################
# 3) TAGS 테이블 (정수화) 로직
################################################
def ensure_tags_table():
    """
    TAGS 테이블이 없으면 생성
    tag_id INT AUTO_INCREMENT, tag_name VARCHAR(255) UNIQUE
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            create_sql = """
            CREATE TABLE IF NOT EXISTS TAGS (
                tag_id INT AUTO_INCREMENT PRIMARY KEY,
                tag_name VARCHAR(255) NOT NULL UNIQUE
            )
            """
            cur.execute(create_sql)
            conn.commit()
    finally:
        conn.close()

def get_or_create_tag_id_in_db(tag_name):
    """
    문자열 태그 -> tag_id
    만약 DB에 없으면 INSERT (자동 생성)
    """
    conn = get_connection()
    the_id = None
    try:
        with conn.cursor() as cur:
            sel_sql = "SELECT tag_id FROM TAGS WHERE tag_name=%s"
            cur.execute(sel_sql, (tag_name,))
            row = cur.fetchone()
            if row:
                the_id = row[0]
            else:
                # 만약 '공식 TAGS'만 허용하고 싶다면 여기서 '스킵' 할 수도 있다.
                ins_sql = "INSERT INTO TAGS (tag_name) VALUES (%s)"
                cur.execute(ins_sql, (tag_name,))
                conn.commit()
                the_id = cur.lastrowid
    finally:
        conn.close()
    return the_id

def convert_tags_to_int_list(tag_list):
    """
    문자열 태그 배열 -> 정수 ID 배열
    TAGS 테이블 참고 (없으면 INSERT)
    """
    int_list = []
    for t in tag_list:
        tag_id = get_or_create_tag_id_in_db(t)  # 없으면 새로 생성
        if tag_id:
            int_list.append(tag_id)
    return int_list

################################################
# 4) +버튼 태그 크롤 함수
################################################
def fetch_tags_via_plus_button(app_id, driver):
    from selenium.common.exceptions import NoSuchElementException
    result = {"app_id": app_id, "name": None, "user_tags": []}

    url = f"https://store.steampowered.com/app/{app_id}"
    driver.get(url)
    time.sleep(0.5)

    # (A) 게임 이름
    try:
        name_elem = driver.find_element(By.CSS_SELECTOR, ".apphub_AppName")
        result["name"] = name_elem.text.strip()
    except NoSuchElementException:
        pass

    # (B) + 버튼
    try:
        plus_btn = driver.find_element(By.CSS_SELECTOR, "div.app_tag.add_button")
        plus_btn.click()
        time.sleep(1)
    except NoSuchElementException:
        print(f"[WARN] +버튼 없음 app_id={app_id}")
        return result

    # (C) 팝업 태그
    try:
        tag_elems = driver.find_elements(By.CSS_SELECTOR, "#app_tagging_modal a.app_tag")
        tags = [el.text.strip() for el in tag_elems if el.text.strip()]
        result["user_tags"] = tags
    except:
        print(f"[WARN] 태그 팝업 수집 실패 app_id={app_id}")

    return result

################################################
# 5) 메인 로직
################################################
def main():
    # 1) TEST_SIMILAR_GAMES 테이블에 user_tags 컬럼 없으면 추가
    ensure_user_tags_column_in_test_table()

    # 2) TAGS 테이블도 보장 (정수화에 필요)
    ensure_tags_table()

    # 3) TEST_SIMILAR_GAMES 모든 행
    rows = fetch_all_test_similar_rows()
    print(f"[INFO] TEST_SIMILAR_GAMES 전체 행 수: {len(rows)}")

    # 4) 웹드라이버 + 스팀 로그인
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # 필요시
    options.add_argument("--disable-gpu")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    login_url = "https://store.steampowered.com/login/"
    driver.get(login_url)
    print("\n[안내] 스팀 로그인 페이지가 열렸습니다.")
    print("브라우저에서 직접 아이디/비번/2차인증을 마친 뒤, 콘솔에 Enter를 눌러주세요.")
    input("로그인 완료 후 Enter...")

    try:
        total = len(rows)
        for i, (row_id, base_app_id, rec_app_id) in enumerate(rows, start=1):
            print(f"\n[{i}/{total}] row_id={row_id}, base_app={base_app_id}, recommended_app={rec_app_id}")

            # (A) 기존 user_tags (int list)
            old_int_list = get_current_user_tags_in_db(row_id)

            # (B) 새로 +버튼 태그 크롤 -> 문자열 리스트
            data = fetch_tags_via_plus_button(rec_app_id, driver)
            str_tags = data.get("user_tags", [])

            # (C) 문자열 태그 -> 정수 태그 ID (TAGS 테이블 참조)
            new_int_list = convert_tags_to_int_list(str_tags)
            new_int_list.sort()  # 정렬하면 순서 문제로 인한 불필요한 갱신 방지

            # 비교
            if old_int_list == new_int_list:
                print(" => 태그 동일 => 업데이트 스킵")
                continue

            # (D) DB 업데이트
            user_tags_json = json.dumps(new_int_list, ensure_ascii=False)
            update_user_tags_in_test_table(row_id, user_tags_json)
            print(f"  기존: {old_int_list}, 새로: {new_int_list}")
            print(f"  => 변경 발생, DB 업데이트 완료")

    finally:
        driver.quit()

    print("\n[DONE] TEST_SIMILAR_GAMES user_tags (정수화) 업데이트 완료!")


if __name__ == "__main__":
    main()
