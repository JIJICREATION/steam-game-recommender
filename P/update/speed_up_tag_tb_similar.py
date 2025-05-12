import os
import time
import json
import pymysql
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

########################################
# 1) DB 연결 & 환경
########################################
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

def ensure_user_tags_column_in_similar_games():
    """
    SIMILAR_GAMES 테이블에 user_tags 컬럼이 없으면 JSON 타입으로 추가.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
            ALTER TABLE SIMILAR_GAMES
                ADD COLUMN IF NOT EXISTS user_tags JSON NULL
            """
            try:
                cur.execute(sql)
                conn.commit()
            except pymysql.err.OperationalError as e:
                # 1060 = 이미 컬럼 존재
                if e.args and e.args[0] == 1060:
                    print("[INFO] 'user_tags' 컬럼 이미 존재. 스킵")
                else:
                    raise e
    finally:
        conn.close()

def ensure_tags_table():
    """
    TAGS 테이블이 없으면 생성,
    tag_id 컬럼이 AUTO_INCREMENT가 아니면 ALTER TABLE로 수정
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1) 우선 CREATE TABLE IF NOT EXISTS
            create_sql = """
            CREATE TABLE IF NOT EXISTS TAGS (
                tag_id INT AUTO_INCREMENT PRIMARY KEY,
                tag_name VARCHAR(255) NOT NULL UNIQUE
            )
            """
            cur.execute(create_sql)
            conn.commit()

            # 2) 이미 존재하는 경우에도 'tag_id'가 AUTO_INCREMENT로
            #    확실히 설정되도록 ALTER TABLE 수행
            alter_sql = """
            ALTER TABLE TAGS
            MODIFY COLUMN tag_id INT NOT NULL AUTO_INCREMENT,
            ADD PRIMARY KEY (tag_id);
            """
            try:
                cur.execute(alter_sql)
                conn.commit()
            except pymysql.err.OperationalError as e:
                print(f"[WARN] ALTER TABLE TAGS 실패 또는 필요 없음 => {e}")
        print("[DB] TAGS 테이블 준비 완료 (AUTO_INCREMENT 보장).")
    finally:
        conn.close()

########################################
# 2) SIMILAR_GAMES 접근 함수
########################################
def fetch_all_similar_games_rows():
    """
    SIMILAR_GAMES 테이블 모든 행의 (game_app_id, recommended_app_id) 반환
    """
    conn = get_connection()
    rows = []
    try:
        with conn.cursor() as cur:
            # id 컬럼 없이 2개만 SELECT
            sql = "SELECT game_app_id, recommended_app_id FROM SIMILAR_GAMES"
            cur.execute(sql)
            rows = cur.fetchall()
    finally:
        conn.close()
    return rows

def get_current_user_tags_in_db(game_app_id, recommended_app_id):
    """
    SIMILAR_GAMES.user_tags (JSON 배열)를 파이썬 list[int]로 변환.
    없거나 NULL이면 빈 리스트.
    """
    conn = get_connection()
    user_tags_json = None
    try:
        with conn.cursor() as cur:
            sel_sql = """
            SELECT user_tags
              FROM SIMILAR_GAMES
             WHERE game_app_id=%s
               AND recommended_app_id=%s
            """
            cur.execute(sel_sql, (game_app_id, recommended_app_id))
            row = cur.fetchone()
            if row:
                user_tags_json = row[0]
    finally:
        conn.close()

    if not user_tags_json:
        return []
    try:
        return json.loads(user_tags_json)
    except:
        return []

def update_user_tags_in_similar_games(game_app_id, recommended_app_id, tags_json):
    """
    SIMILAR_GAMES.user_tags 업데이트 (id 컬럼 없이)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
            UPDATE SIMILAR_GAMES
               SET user_tags = %s
             WHERE game_app_id=%s
               AND recommended_app_id=%s
            """
            cur.execute(sql, (tags_json, game_app_id, recommended_app_id))
        conn.commit()
    finally:
        conn.close()

########################################
# 3) 태그(TAGS) 테이블과 동기화 (문자열→숫자ID)
########################################
def get_or_create_tag_id_in_db(tag_name):
    """
    DB의 TAGS 테이블에서 tag_name으로 tag_id 조회,
    없으면 INSERT
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
                ins_sql = "INSERT INTO TAGS (tag_name) VALUES (%s)"
                cur.execute(ins_sql, (tag_name,))
                conn.commit()
                the_id = cur.lastrowid
    finally:
        conn.close()
    return the_id

def convert_tags_to_int_list(tag_list, local_mapping):
    """
    문자열 태그 리스트 -> 숫자 태그ID 리스트 (TAGS 테이블 연동).
    이미 존재하는 태그는 기존 tag_id 재사용.
    """
    int_list = []
    for t in tag_list:
        if t in local_mapping:
            tag_id = local_mapping[t]
        else:
            tag_id = get_or_create_tag_id_in_db(t)
            local_mapping[t] = tag_id
        int_list.append(tag_id)
    return int_list

########################################
# 4) 태그 매핑 로컬 JSON
########################################
TAG_JSON_PATH = "tag_dict.json"

def load_tag_mapping():
    if not os.path.exists(TAG_JSON_PATH):
        return {}
    with open(TAG_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if data else {}

def save_tag_mapping(mapping):
    with open(TAG_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

########################################
# 5) 셀레니움: 스팀 로그인 + '+버튼' 태그 크롤
########################################
def steam_manual_login(driver):
    login_url = "https://store.steampowered.com/login/"
    driver.get(login_url)
    print("\n[안내] 스팀 로그인 페이지가 열렸습니다.")
    print("브라우저에서 직접 로그인(2차 인증, 성인인증 등) 후 콘솔에 Enter를 눌러주세요.")
    input("로그인 완료 후 Enter...")

def fetch_tags_via_plus_button(app_id, driver):
    from selenium.common.exceptions import NoSuchElementException
    url = f"https://store.steampowered.com/app/{app_id}"
    driver.get(url)
    time.sleep(2)

    try:
        plus_btn = driver.find_element(By.CSS_SELECTOR, "div.app_tag.add_button")
        plus_btn.click()
        time.sleep(1)
    except NoSuchElementException:
        print(f"[WARN] +버튼 없음 app_id={app_id}")
        return []

    try:
        tag_elems = driver.find_elements(By.CSS_SELECTOR, "#app_tagging_modal a.app_tag")
        tags = [el.text.strip() for el in tag_elems if el.text.strip()]
        return tags
    except:
        print(f"[WARN] 태그 팝업 수집 실패 app_id={app_id}")
        return []

########################################
# 6) MAIN
########################################
def main():
    # 1) DB 컬럼/테이블 보장
    ensure_user_tags_column_in_similar_games()
    ensure_tags_table()

    # 2) 모든 행 가져오기
    rows = fetch_all_similar_games_rows()
    print(f"[INFO] SIMILAR_GAMES 전체 행 수: {len(rows)}")
    if not rows:
        print("[INFO] 처리할 데이터가 없습니다. 종료.")
        return

    # 3) 로컬 태그 매핑 로드
    local_tag_mapping = load_tag_mapping()

    # 4) 브라우저 열기 (헤드풀 모드) + 로그인
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        steam_manual_login(driver)

        # (A) recommended_app_id를 기준으로 묶기
        from collections import defaultdict
        grouped_by_reco = defaultdict(list)
        for (game_app_id, recommended_app_id) in rows:
            grouped_by_reco[recommended_app_id].append(game_app_id)

        print(f"[INFO] 중복 포함한 recommended_app_id 개수: {len(grouped_by_reco)}")

        reco_cache = {}
        total_unique_reco = len(grouped_by_reco)
        cnt = 0

        for reco_app_id, game_id_list in grouped_by_reco.items():
            cnt += 1
            print(f"\n[{cnt}/{total_unique_reco}] recommended_app_id={reco_app_id}, 관련 row 수={len(game_id_list)}")

            # (B) 캐시 확인
            if reco_app_id in reco_cache:
                str_tags = reco_cache[reco_app_id]
                print(f" => 이미 크롤 완료된 app_id={reco_app_id}, 태그 재사용.")
            else:
                # 처음 크롤
                str_tags = fetch_tags_via_plus_button(reco_app_id, driver)
                reco_cache[reco_app_id] = str_tags
                print(f" => 새로 크롤: {str_tags}")

            # (C) 문자열 태그 -> tag_id 리스트
            new_int_list = convert_tags_to_int_list(str_tags, local_tag_mapping)
            tags_json = json.dumps(new_int_list, ensure_ascii=False)

            # (D) 매핑된 모든 game_app_id 에 대해 user_tags 갱신
            for g_id in game_id_list:
                old_int_list = get_current_user_tags_in_db(g_id, reco_app_id)
                if old_int_list == new_int_list:
                    print(f"    (game_app_id={g_id}, reco_app_id={reco_app_id}) => 태그 동일, 스킵")
                else:
                    update_user_tags_in_similar_games(g_id, reco_app_id, tags_json)
                    print(f"    (game_app_id={g_id}, reco_app_id={reco_app_id}) => DB 업데이트 완료: {new_int_list}")

    finally:
        driver.quit()

    # 6) 로컬 태그 매핑 저장
    save_tag_mapping(local_tag_mapping)
    print("\n[DONE] 전체 크롤 완료.")
    print("    - tag_id는 기존 태그명을 재사용하므로 바뀌지 않습니다.")
    print("    - 중복 recommended_app_id는 한 번만 크롤했습니다.")

if __name__ == "__main__":
    main()
