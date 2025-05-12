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
# 1) DB 연결
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

########################################
# 2) user_tags='[]' 또는 NULL인 행 조회 (game_app_id ASC)
########################################
def fetch_empty_array_user_tags_rows():
    """
    SIMILAR_GAMES 테이블에서 user_tags가 '[]' 또는 NULL인 행의 (game_app_id, recommended_app_id)만 조회
    """
    conn = get_connection()
    rows = []
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT game_app_id, recommended_app_id
                FROM SIMILAR_GAMES
                WHERE user_tags = '[]'
                   OR user_tags IS NULL
                ORDER BY game_app_id ASC
            """
            cur.execute(sql)
            rows = cur.fetchall()  # [(game_app_id, recommended_app_id), ...]
    finally:
        conn.close()
    return rows

########################################
# 3) +버튼 태그 크롤
########################################
def fetch_tags_via_plus_button(app_id, driver):
    from selenium.common.exceptions import NoSuchElementException
    url = f"https://store.steampowered.com/app/{app_id}"
    driver.get(url)
    time.sleep(1)

    # +버튼 클릭
    try:
        plus_btn = driver.find_element(By.CSS_SELECTOR, "div.app_tag.add_button")
        plus_btn.click()
        time.sleep(1)
    except NoSuchElementException:
        print(f"[WARN] +버튼 없음 app_id={app_id}")
        return []

    # 팝업 태그 수집
    try:
        tag_elems = driver.find_elements(By.CSS_SELECTOR, "#app_tagging_modal a.app_tag")
        tags = [el.text.strip() for el in tag_elems if el.text.strip()]
        return tags
    except:
        print(f"[WARN] 태그 팝업 수집 실패 app_id={app_id}")
        return []

########################################
# 4) 태그(TABLE) 동기화 (문자열 → 숫자 ID)
########################################
def get_or_create_tag_id_in_db(tag_name):
    """
    TAGS 테이블에서 tag_name으로 tag_id 조회.
    없으면 INSERT 후, 새 tag_id 반환
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
    문자열 태그 리스트 → tag_id 리스트 (TAGS 연동)
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
# 5) 태그 매핑 로컬 JSON
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
# 6) DB 업데이트 (id 없이, (game_app_id, recommended_app_id)로 처리)
########################################
def update_user_tags_in_similar_games(game_app_id, recommended_app_id, tags_json):
    """
    크롤링 결과(문자열/정수 리스트 JSON)를 SIMILAR_GAMES.user_tags에 업데이트.
    테이블에 'id' 컬럼 없이, (game_app_id, recommended_app_id)를 조건으로 사용
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
            UPDATE SIMILAR_GAMES
               SET user_tags = %s
             WHERE game_app_id = %s
               AND recommended_app_id = %s
            """
            cur.execute(sql, (tags_json, game_app_id, recommended_app_id))
        conn.commit()
    finally:
        conn.close()

########################################
# 7) MAIN
########################################
def main():
    # (A) 브라우저 열기 (창 띄움)
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # (B) 스팀 로그인
        driver.get("https://store.steampowered.com/login/")
        print("[안내] 스팀 로그인(성인인증 등) 후 콘솔에 Enter를 눌러주세요.")
        input()

        # (C) user_tags='[]' 또는 NULL인 행만 가져오기
        rows = fetch_empty_array_user_tags_rows()
        print(f"[INFO] 재크롤 대상 행 수(user_tags='[]' or NULL): {len(rows)}")
        if not rows:
            print("[INFO] 빈 배열/NULL인 레코드가 없습니다. 종료.")
            return

        # (D) recommended_app_id를 기준으로 그룹화
        from collections import defaultdict
        grouped = defaultdict(list)
        for (game_app_id, reco_app_id) in rows:
            grouped[reco_app_id].append(game_app_id)

        print(f"[INFO] unique recommended_app_id 개수: {len(grouped)}")

        # (E) 캐시 (reco_app_id별 문자열 태그)
        tags_cache = {}

        # (F) 태그 문자열 → 태그 ID 매핑 캐시
        local_mapping = load_tag_mapping()

        # (G) 그룹 순회
        total = len(grouped)
        for i, (reco_app_id, game_ids) in enumerate(grouped.items(), start=1):
            print(f"\n[{i}/{total}] app_id={reco_app_id}, 관련 game_app_id 개수={len(game_ids)}")

            # 캐시 확인
            if reco_app_id in tags_cache:
                str_tags = tags_cache[reco_app_id]
                print(f" => 캐시 태그 재사용: {str_tags}")
            else:
                # 새로 크롤
                str_tags = fetch_tags_via_plus_button(reco_app_id, driver)
                tags_cache[reco_app_id] = str_tags
                print(f" => 새로 크롤: {str_tags}")

            # 문자열 태그 -> tag_id 리스트
            int_tags_list = convert_tags_to_int_list(str_tags, local_mapping)
            tags_json = json.dumps(int_tags_list, ensure_ascii=False)

            # 모든 (game_app_id, reco_app_id)에 대해 DB 업데이트
            for g_id in game_ids:
                update_user_tags_in_similar_games(g_id, reco_app_id, tags_json)
                print(f"   game_app_id={g_id} => 업데이트 완료: {tags_json}")

        # (H) 로컬 매핑 파일 최종 저장
        save_tag_mapping(local_mapping)

    finally:
        driver.quit()

    print("\n[DONE] user_tags='[]' or NULL 레코드들 재크롤링 완료 (game_app_id ASC).")

if __name__ == "__main__":
    main()
