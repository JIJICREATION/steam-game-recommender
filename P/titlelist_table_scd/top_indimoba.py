import os
import time
import requests
import pymysql
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup

##################################################
# 1) Env & DB 설정
##################################################
load_dotenv()

dbuser = os.getenv('dbuser')
password = os.getenv('password')
host = os.getenv('host')
port = int(os.getenv('port', 3306))
dbname = os.getenv('name')

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
# 2) TOPINDIMOBA_GAME SCD 테이블 생성
##################################################
def create_scd_table_TOPINDIMOBA_GAME():
    create_sql = """
    CREATE TABLE IF NOT EXISTS TOPINDIMOBA_GAME (
      app_id       BIGINT NOT NULL,
      name         VARCHAR(255),
      price        FLOAT,
      release_date VARCHAR(50),
      start_date   DATETIME NOT NULL,
      end_date     DATETIME NOT NULL DEFAULT '9999-12-31',
      PRIMARY KEY (app_id, start_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(create_sql)
        conn.commit()
        print("[DB] SCD 테이블 TOPINDIMOBA_GAME이 준비되었습니다.")
    finally:
        conn.close()

##################################################
# 3) TOPINDIMOBA_GAME 업서트 함수 (SCD Type2)
##################################################
def upsert_TOPINDIMOBA_GAME_scd_version(app_id, name, price, release_date):
    """
    SCD Type2 Upsert (start_date / end_date 버전):
      - 현재 활성 레코드: end_date = '9999-12-31'
      - 기존 데이터와 비교하여 변경 사항이 있으면 기존 레코드의 end_date를 현재 시각(now_str)으로 업데이트한 후,
        새 버전을 삽입 (새 레코드의 end_date는 '9999-12-31')
      - 값이 동일하면 업데이트하지 않음.
    
    인자:
      - app_id: 게임의 App ID
      - name: 게임명
      - price: 가격 (FLOAT)
      - release_date: 출시일 정보 (문자열)
    """
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    start_date = now_str  # 새 레코드의 시작 시점
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sel_sql = """
            SELECT name, price, release_date
              FROM TOPINDIMOBA_GAME
             WHERE app_id = %s
               AND end_date = '9999-12-31'
             ORDER BY start_date DESC
             LIMIT 1
            """
            cur.execute(sel_sql, (app_id,))
            row = cur.fetchone()

            if not row:
                # 첫 삽입: 활성 레코드 생성
                ins_sql = """
                INSERT INTO TOPINDIMOBA_GAME
                 (app_id, name, price, release_date, start_date, end_date)
                VALUES
                 (%s, %s, %s, %s, %s, '9999-12-31')
                """
                cur.execute(ins_sql, (
                    app_id,
                    name or "",
                    float(price or 0.0),
                    release_date or "",
                    start_date
                ))
                print(f"[INSERT] app_id={app_id}, name='{name}' 삽입됨.")
            else:
                old_name, old_price, old_release_date = row
                old_name = old_name or ""
                old_price = float(old_price or 0.0)
                old_release_date = old_release_date or ""
                
                new_name = name or ""
                new_price = float(price or 0.0)
                new_release_date = release_date or ""
                
                changed = (
                    old_name != new_name or
                    old_price != new_price or
                    old_release_date != new_release_date
                )
                if changed:
                    # 기존 활성 레코드 만료: end_date 업데이트
                    expire_sql = """
                    UPDATE TOPINDIMOBA_GAME
                       SET end_date = %s
                     WHERE app_id = %s
                       AND end_date = '9999-12-31'
                    """
                    cur.execute(expire_sql, (now_str, app_id))
                    # 새 버전 삽입
                    ins_sql = """
                    INSERT INTO TOPINDIMOBA_GAME
                     (app_id, name, price, release_date, start_date, end_date)
                    VALUES
                     (%s, %s, %s, %s, %s, '9999-12-31')
                    """
                    cur.execute(ins_sql, (
                        app_id,
                        new_name,
                        new_price,
                        new_release_date,
                        start_date
                    ))
                    print(f"[UPDATE] app_id={app_id}, 새 버전 업데이트됨.")
                else:
                    print(f"[NO CHANGE] app_id={app_id} - 변경 사항 없음.")
        conn.commit()
    finally:
        conn.close()

##################################################
# 4) TRENDING 게임 크롤링 (인디+MOBA 최신 인기 게임)
##################################################
TRENDING_URL = "https://store.steampowered.com/search/?sort_by=Released_DESC&tags=492%2C1718&category1=998&filter=topsellers&ndl=1"
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})

def crawl_TOPINDIMOBA_GAMEs():
    try:
        resp = session.get(TRENDING_URL, timeout=10)
        resp.raise_for_status()
        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # 각 게임은 "a" 태그의 class "search_result_row"에 있음
        game_links = soup.find_all("a", class_="search_result_row")
        games = []
        for link in game_links:
            app_id = link.get("data-ds-appid")
            if not app_id:
                continue
            
            title_tag = link.find("span", class_="title")
            name = title_tag.get_text(strip=True) if title_tag else ""
            
            price_div = link.find("div", class_="search_price")
            if price_div:
                price_text = " ".join(price_div.stripped_strings)
                parts = price_text.split()
                price_value = parts[-1] if parts else ""
            else:
                price_value = ""
            
            release_div = link.find("div", class_="search_released")
            release_date = release_div.get_text(strip=True) if release_div else ""
            
            games.append({
                "app_id": int(app_id),
                "name": name,
                "price": price_value,
                "release_date": release_date
            })
        return games
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] crawl_TOPINDIMOBA_GAMEs 실패: {e}")
        return []

##################################################
# 5) MAIN 함수
##################################################
def main():
    # A) TOPINDIMOBA_GAME 테이블 생성
    create_scd_table_TOPINDIMOBA_GAME()

    # B) 트렌딩 게임 크롤링
    games = crawl_TOPINDIMOBA_GAMEs()
    print(f"\n[INFO] 총 크롤링된 게임 수: {len(games)}")

    # C) TOPINDIMOBA_GAME 테이블에 SCD 방식 업서트
    for game in games:
        app_id = game.get("app_id")
        name = game.get("name")
        price = game.get("price")
        release_date = game.get("release_date")
        
        if not app_id:
            print("[SKIP] app_id 정보 없음")
            continue
        
        upsert_TOPINDIMOBA_GAME_scd_version(
            app_id,
            name,
            price,
            release_date
        )
    print("[DONE] 모든 트렌딩 게임 데이터가 TOPINDIMOBA_GAME 테이블에 업서트되었습니다.")

if __name__ == "__main__":
    main()
