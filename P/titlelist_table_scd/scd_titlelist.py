import os
import time
import requests
import pymysql
from datetime import datetime
from dotenv import load_dotenv

##################################################
# 1) Env & DB
##################################################
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

##################################################
# 2) Create SCD Table: TITLELIST
##################################################
def create_scd_table_titlelist():
    create_sql = """
    CREATE TABLE IF NOT EXISTS TITLELIST (
      app_id      BIGINT NOT NULL,
      name        VARCHAR(255),
      price_us    FLOAT,
      releaseYear VARCHAR(10),
      userScore   FLOAT,
      valid_from  DATETIME NOT NULL,
      valid_to    DATETIME DEFAULT NULL,
      PRIMARY KEY (app_id, valid_from)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(create_sql)
        conn.commit()
        print("[DB] SCD table TITLELIST is ready.")
    finally:
        conn.close()

##################################################
# 3) Upsert function (SCD Type2)
##################################################
def upsert_titlelist_scd_version(app_id, name, price_us, releaseYear, userScore):
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # begin transaction if needed
            # conn.begin()
            # 1) select current version
            sel_sql = """
            SELECT name, price_us, releaseYear, userScore
              FROM TITLELIST
             WHERE app_id=%s
               AND valid_to IS NULL
             ORDER BY valid_from DESC
             LIMIT 1
            """
            cur.execute(sel_sql, (app_id,))
            row = cur.fetchone()

            if not row:
                # first insert
                ins_sql = """
                INSERT INTO TITLELIST
                 (app_id, name, price_us, releaseYear, userScore,
                  valid_from, valid_to)
                VALUES
                 (%s, %s, %s, %s, %s, %s, NULL)
                """
                cur.execute(ins_sql, (
                    app_id, name or "", float(price_us or 0.0),
                    releaseYear or "", float(userScore or 0.0),
                    now_str
                ))
                print(f"[INSERT] app_id={app_id}, first version.")
            else:
                old_name, old_price, old_year, old_score = row
                # None safe
                if not old_name: old_name = ""
                if not old_year: old_year = ""
                if not old_price: old_price = 0.0
                if not old_score: old_score = 0.0

                new_name = name or ""
                new_price = float(price_us or 0.0)
                new_year = releaseYear or ""
                new_score = float(userScore or 0.0)

                changed = (
                    old_name != new_name or
                    float(old_price) != new_price or
                    old_year != new_year or
                    float(old_score) != new_score
                )
                if changed:
                    # expire old version
                    expire_sql = """
                    UPDATE TITLELIST
                       SET valid_to=%s
                     WHERE app_id=%s
                       AND valid_to IS NULL
                    """
                    cur.execute(expire_sql, (now_str, app_id))

                    # insert new version
                    ins_sql = """
                    INSERT INTO TITLELIST
                     (app_id, name, price_us, releaseYear, userScore,
                      valid_from, valid_to)
                    VALUES
                     (%s, %s, %s, %s, %s, %s, NULL)
                    """
                    cur.execute(ins_sql, (
                        app_id, new_name, new_price, new_year, new_score,
                        now_str
                    ))
                    print(f"[UPDATE] app_id={app_id}, new version.")
                else:
                    print(f"[NO CHANGE] app_id={app_id}")

        conn.commit()
    finally:
        conn.close()

##################################################
# 4) Algolia Crawling
##################################################
BASE_URL = (
    f"https://{ALGOLIA_APP_ID.lower()}-dsn.algolia.net/1/indexes/*/queries"
    "?x-algolia-agent=Algolia%20for%20JavaScript%20(5.21.0)%3B%20Lite%20(5.21.0)"
    "%3B%20Browser%3B%20instantsearch.js%20(4.78.0)%3B%20JS%20Helper%20(3.24.2)"
    f"&x-algolia-api-key={ALGOLIA_API_KEY}"
    f"&x-algolia-application-id={ALGOLIA_APP_ID}"
)
session = requests.Session()
session.headers.update({
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://steamdb.info/instantsearch/",
    "Origin": "https://steamdb.info"
})

def fetch_page(page, hits_per_page=50):
    payload = {
        "requests": [
            {
                "indexName": "steamdb",
                "attributesToHighlight": ["name"],
                "attributesToRetrieve": [
                    "lastUpdated",
                    "small_capsule",
                    "name",
                    "price_us",
                    "releaseYear",
                    "userScore"
                ],
                "facetFilters": ["tags:Indie", "tags:MOBA", ["appType:Game"]],
                "facets": [
                    "appType","categories","developer","followers","hardwareCategories",
                    "languages","languagesAudio","languagesSubtitles","multiplayerCategories",
                    "price_us","publisher","releaseYear","reviews","tags","technologies","userScore"
                ],
                "highlightPostTag": "__/ais-highlight__",
                "highlightPreTag": "__ais-highlight__",
                "hitsPerPage": hits_per_page,
                "maxValuesPerFacet": 200,
                "page": page,
                "query": ""
            }
        ]
    }
    try:
        resp = session.post(BASE_URL, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] fetch_page({page}) failed: {e}")
        return None

def crawl_all_pages(hits_per_page=100, delay=0.5):
    all_hits = []
    page_num = 0
    while True:
        print(f"[INFO] Fetching page={page_num} (hitsPerPage={hits_per_page})")
        data = fetch_page(page_num, hits_per_page=hits_per_page)
        if not data:
            break

        results_array = data.get("results", [])
        if not results_array:
            break

        main_result = results_array[0]
        hits = main_result.get("hits", [])
        if not hits:
            break

        all_hits.extend(hits)
        print(f"[INFO] page={page_num} => {len(hits)} hits (total so far: {len(all_hits)})")

        nb_pages = main_result.get("nbPages", 1)
        page_num += 1
        if page_num >= nb_pages:
            break

        time.sleep(delay)
    return all_hits

##################################################
# 5) main
##################################################
def main():
    # A) create SCD table
    create_scd_table_titlelist()

    # B) crawl
    hits = crawl_all_pages(hits_per_page=100, delay=0.5)
    print(f"\n[INFO] total crawled: {len(hits)}")

    # C) upsert into TITLELIST (SCD)
    for h in hits:
        # parse
        app_id = h.get("objectID")
        name = h.get("name","")
        price_us = h.get("price_us",0.0)
        releaseYear = h.get("releaseYear","")
        userScore = h.get("userScore",0.0)

        if not app_id:
            print("[SKIP] no app_id/objectID in data item")
            continue
        
        upsert_titlelist_scd_version(
            app_id,
            name,
            price_us,
            releaseYear,
            userScore
        )
    print("[DONE] All hits upserted to SCD TITLELIST.")

if __name__ == "__main__":
    main()
