# update_titlelist.py
# 0323 TITLELIST 테이블 생성
# STEAMDB 크롤링 시 -> ********** API키 변경 확인해야함 *******
# 이전 STEAM LOGIN 없이 크롤링 -> 로그인 후 태그 크롤링
# 태그 매핑 -> 태그 ID로 변환
# 태그 ID로 TITLELIST에 SCD 업서트


import os
import time
import json
import requests
import pymysql
from datetime import datetime
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

########################################
# 1) ENV & DB SETUP
########################################
load_dotenv()

dbuser = os.getenv('dbuser')
password = os.getenv('password')
host = os.getenv('host')
port = int(os.getenv('port', 3306))
dbname = os.getenv('name')

ALGOLIA_APP_ID = os.getenv("ALGOLIA_APP_ID", "94HE6YATEI")
ALGOLIA_API_KEY = os.getenv("ALGOLIA_API_KEY", "")

def get_connection():
    return pymysql.connect(
        host=host,
        user=dbuser,
        password=password,
        database=dbname,
        port=port,
        charset="utf8mb4"
    )

########################################
# 2) CREATE SCD TABLE
########################################
# def create_scd_table():
#     create_sql = """
#     CREATE TABLE IF NOT EXISTS TITLELIST (
#       app_id      BIGINT      NOT NULL,
#       name        VARCHAR(255),
#       user_tags   TEXT,       -- JSON [1,2,3]
#       price_us    FLOAT,
#       releaseYear VARCHAR(10),
#       userScore   FLOAT,
#       start_date  DATETIME    NOT NULL,
#       end_date    DATETIME    NOT NULL DEFAULT '9999-12-31',
#       PRIMARY KEY (app_id, start_date)
#     ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
#     """
#     conn = get_connection()
#     try:
#         with conn.cursor() as cur:
#             cur.execute(create_sql)
#         conn.commit()
#         print("[DB] SCD table 'TITLELIST' ready.")
#     finally:
#         conn.close()

########################################
# 3) SCD Upsert
########################################
def upsert_titlelist_scd_version(
    app_id, name, price_us, releaseYear, userScore,
    user_tags_json="",  # 태그 배열의 JSON 문자열. 예: "[1,2,3]"
    start_date=None
):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not start_date:
        start_date = now_str

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sel_sql = """
            SELECT name, user_tags, price_us, releaseYear, userScore
              FROM TITLELIST
             WHERE app_id=%s
               AND end_date='9999-12-31'
             ORDER BY start_date DESC
             LIMIT 1
            """
            cur.execute(sel_sql, (app_id,))
            row = cur.fetchone()

            if not row:
                # 첫 Insert
                ins_sql = """
                INSERT INTO TITLELIST
                 (app_id, name, user_tags, price_us, releaseYear, userScore,
                  start_date, end_date)
                VALUES
                 (%s, %s, %s, %s, %s, %s, %s, '9999-12-31')
                """
                cur.execute(ins_sql, (
                    app_id,
                    name or "",
                    user_tags_json or "",
                    float(price_us or 0.0),
                    releaseYear or "",
                    float(userScore or 0.0),
                    start_date
                ))
                print(f"[INSERT] app_id={app_id}, name={name}, userScore={userScore} tags={user_tags_json}")
            else:
                old_name, old_tags, old_price, old_year, old_score = row
                old_name = old_name or ""
                old_tags = old_tags or ""
                old_year = old_year or ""
                old_price = float(old_price or 0.0)
                old_score = float(old_score or 0.0)

                new_name = name or ""
                new_tags = user_tags_json or ""
                new_price = float(price_us or 0.0)
                new_year = releaseYear or ""
                new_score = float(userScore or 0.0)

                changed = (
                    old_name != new_name or
                    old_tags != new_tags or
                    old_price != new_price or
                    old_year != new_year or
                    old_score != new_score
                )
                if changed:
                    expire_sql = """
                    UPDATE TITLELIST
                       SET end_date=%s
                     WHERE app_id=%s
                       AND end_date='9999-12-31'
                    """
                    cur.execute(expire_sql, (now_str, app_id))

                    ins_sql = """
                    INSERT INTO TITLELIST
                     (app_id, name, user_tags, price_us, releaseYear, userScore,
                      start_date, end_date)
                    VALUES
                     (%s, %s, %s, %s, %s, %s, %s, '9999-12-31')
                    """
                    cur.execute(ins_sql, (
                        app_id,
                        new_name,
                        new_tags,
                        new_price,
                        new_year,
                        new_score,
                        start_date
                    ))
                    print(f"[UPDATE] app_id={app_id}, changed => {new_tags}")
                else:
                    print(f"[NO CHANGE] app_id={app_id}")

        conn.commit()
    finally:
        conn.close()

########################################
# 4) Algolia(steamdb) Crawling
########################################
session = requests.Session()

def fetch_page(page=0, hits_per_page=50):
    # (키 & 인덱스) => 유효한지 주의!
    base_url = (
        f"https://{ALGOLIA_APP_ID.lower()}-dsn.algolia.net/1/indexes/*/queries"
        "?x-algolia-agent=Algolia%20for%20JavaScript..."
        f"&x-algolia-api-key={ALGOLIA_API_KEY}"
        f"&x-algolia-application-id={ALGOLIA_APP_ID}"
    )
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://steamdb.info/instantsearch/",
        "Origin": "https://steamdb.info"
    })
    payload = {
        "requests": [
            {
                "indexName": "steamdb",
                "attributesToHighlight": ["name"],
                "attributesToRetrieve": [
                    "lastUpdated", "small_capsule", "name",
                    "price_us", "releaseYear", "userScore"
                ],
                "facetFilters": ["tags:Indie", "tags:MOBA", ["appType:Game"]],
                "facets": [],
                "hitsPerPage": hits_per_page,
                "page": page,
                "query": ""
            }
        ]
    }
    try:
        resp = session.post(base_url, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"[ERROR] fetch_page({page}) => {e}")
        return None

def crawl_steamdb_all(hits_per_page=50, delay=0.5):
    all_hits = []
    page_num = 0
    while True:
        print(f"[INFO] Fetching page={page_num} (hits_per_page={hits_per_page})")
        data = fetch_page(page=page_num, hits_per_page=hits_per_page)
        if not data: break

        arr = data.get("results", [])
        if not arr: break

        main_result = arr[0]
        hits = main_result.get("hits", [])
        if not hits: break

        all_hits.extend(hits)
        nb_pages = main_result.get("nbPages", 1)
        page_num += 1
        print(f" page={page_num-1} => {len(hits)} hits (total so far={len(all_hits)})")
        if page_num >= nb_pages:
            break
        time.sleep(delay)
    print(f"[DONE] total {len(all_hits)} from Algolia steamdb.")
    return all_hits

########################################
# 5) 수동 로그인 + 태그 크롤
########################################
def steam_manual_login(driver):
    login_url = "https://store.steampowered.com/login/"
    driver.get(login_url)
    print("스팀 로그인 후 콘솔에 Enter...")
    input()

def fetch_tags_via_plus_button(app_id, driver):
    result = {"app_id": app_id, "name": None, "user_tags": []}
    url = f"https://store.steampowered.com/app/{app_id}"
    driver.get(url)
    time.sleep(2)

    try:
        name_elem = driver.find_element(By.CSS_SELECTOR, ".apphub_AppName")
        result["name"] = name_elem.text.strip()
    except:
        pass

    try:
        plus_btn = driver.find_element(By.CSS_SELECTOR, "div.app_tag.add_button")
        plus_btn.click()
        time.sleep(1)
    except:
        print(f"[WARN] +버튼 fail app_id={app_id}")
        return result

    try:
        tag_elems = driver.find_elements(By.CSS_SELECTOR, "#app_tagging_modal a.app_tag")
        tags = [el.text.strip() for el in tag_elems if el.text.strip()]
        result["user_tags"] = tags
    except:
        print(f"[WARN] popup tag fail app_id={app_id}")

    return result

########################################
# 5-1) 태그 매핑
########################################
TAG_JSON_PATH = "tag_dict.json"

def load_tag_mapping():
    if not os.path.exists(TAG_JSON_PATH):
        return {}, 1
    with open(TAG_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not data:
        return {}, 1
    max_val = max(data.values())
    return data, max_val+1

def save_tag_mapping(mapping):
    with open(TAG_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

def get_tag_id(tag_name, mapping, next_id_ref):
    if tag_name not in mapping:
        mapping[tag_name] = next_id_ref[0]
        next_id_ref[0] += 1
        save_tag_mapping(mapping)
    return mapping[tag_name]

def convert_tags_to_int_list(tag_list, mapping, next_id_ref):
    return [get_tag_id(t, mapping, next_id_ref) for t in tag_list]

########################################
# 6) MAIN
########################################
def main():
    # 1) SCD 테이블
    # create_scd_table()

    # 2) Algolia -> app list
    hits = crawl_steamdb_all(hits_per_page=50, delay=0.5)
    print(f"[INFO] total algolia hits: {len(hits)}")

    # 3) 셀레니움 브라우저 + 수동 로그인
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # 주석처리, 사람 로그인
    options.add_argument("--disable-gpu")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    steam_manual_login(driver)

    # 4) 태그 매핑 로드
    tag_mapping, next_id_val = load_tag_mapping()
    next_id_ref = [next_id_val]

    # 5) for each app => upsert
    for i, h in enumerate(hits):
        objectID = h.get("objectID", "")
        if not objectID.isdigit():
            continue
        app_id = int(objectID)

        name = h.get("name", "")
        price_us = h.get("price_us", 0.0)
        releaseYear = str(h.get("releaseYear", ""))
        userScore = h.get("userScore", 0.0)

        # (A) steam 태그
        tag_info = fetch_tags_via_plus_button(app_id, driver=driver)
        raw_tags = tag_info["user_tags"]
        int_list = convert_tags_to_int_list(raw_tags, tag_mapping, next_id_ref)
        user_tags_json = json.dumps(int_list)

        # (B) SCD 업서트
        upsert_titlelist_scd_version(
            app_id=app_id,
            name=name,  # Algolia의 name vs Steam store name 중 어느 걸 쓸지도 선택 가능
            price_us=price_us,
            releaseYear=releaseYear,
            userScore=userScore,
            user_tags_json=user_tags_json
        )
        print(f"[{i+1}/{len(hits)}] app_id={app_id}, name={name}, tags={raw_tags}")

    driver.quit()
    print("[DONE] Combined Algolia+Steam SCD update done.")

if __name__ == "__main__":
    main()
