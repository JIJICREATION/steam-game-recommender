'''
수빈님의 코드를 연구하기 위해서 복사했던 파일입니다. 
'''

import requests
import mariadb
import os
import time
from dotenv import load_dotenv
from typing import List, Optional, Dict, Any

load_dotenv()

def create_table_if_not_exists(conn: mariadb.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS games (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        app_id VARCHAR(20) UNIQUE NOT NULL,
        price_us DECIMAL(10,2),
        releaseYear YEAR,
        userScore DECIMAL(3,1),
        genre VARCHAR(255) NOT NULL,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
    """)
    conn.commit()

def get_db_connection() -> mariadb.Connection:
    try:
        conn = mariadb.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            autocommit=True
        )
        create_table_if_not_exists(conn)
        return conn
    except mariadb.Error as e:
        print(f"🔴 DB 연결 실패: {e}")
        raise

def clean_price(price) -> Optional[float]:
    try:
        if isinstance(price, str):
            return float(price.replace('$', '').strip())
        return float(price) if price else None
    except:
        return None

def fetch_page(page: int, genres: List[str]) -> Optional[dict]:
    base_url = "https://94he6yatei-dsn.algolia.net/1/indexes/*/queries"
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    
    payload = {
        "requests": [{
            "indexName": "steamdb",
            "attributesToRetrieve": ["name", "objectID", "price_us", "releaseYear", "userScore"],
            "facetFilters": [[f"tags:{g}"] for g in genres] + [["appType:Game"]],
            "hitsPerPage": 50,
            "page": page,
        }]
    }

    try:
        resp = requests.post(
            base_url,
            headers=headers,
            json=payload,
            params={
                "x-algolia-api-key": os.getenv("ALGOLIA_API_KEY"),
                "x-algolia-application-id": os.getenv("ALGOLIA_APP_ID")
            },
            timeout=15
        )
        return resp.json() if resp.status_code == 200 else None
    except Exception as e:
        print(f"🔴 요청 오류: {e}")
        return None

def save_to_db(data: List[Dict[str, Any]], genre: str) -> None:
    if not data:
        return

    query = """
    INSERT INTO TITLELIST (name, app_id, price_us, releaseYear, userScore, genre)
    VALUES (?, ?, ?, ?, ?, ?)
    ON DUPLICATE KEY UPDATE 
        price_us=COALESCE(VALUES(price_us), price_us),
        userScore=COALESCE(VALUES(userScore), userScore),
        genre=VALUES(genre)
    """

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        params = []
        for item in data:
            params.append((
                item.get('name', ''),
                item.get('app_id', ''),
                item.get('price_us'),
                item.get('releaseYear'),
                item.get('userScore'),
                genre
            ))
        
        cursor.executemany(query, params)
        print(f"✅ 성공적으로 {len(data)}개 데이터 저장")
        
    except mariadb.Error as e:
        print(f"🔴 DB 오류: {e}")
        print(f"문제 발생 데이터: {params[:3]}")  # 최초 3개 데이터 출력
    finally:
        if 'conn' in locals():
            try:
                conn.close()
            except:
                pass

def crawl_steam(genres: List[str], max_pages: int = 5) -> None:
    for page in range(max_pages):
        print(f"📃 페이지 {page+1} 처리 중...")
        
        result = fetch_page(page, genres)
        if not result or not result.get('results'):
            print("⏹ 추가 데이터 없음")
            break
            
        hits = result['results'][0].get('hits', [])
        processed = [{
            'name': h.get('name'),
            'app_id': h.get('objectID'),
            'price_us': clean_price(h.get('price_us')),
            'releaseYear': int(h['releaseYear']) if h.get('releaseYear') else None,
            'userScore': float(h['userScore']) if h.get('userScore') else None
        } for h in hits if h.get('objectID')]

        save_to_db(processed, ",".join(genres))
        time.sleep(1.5)

if __name__ == "__main__":
    crawl_steam(
        genres=["Indie", "MOBA"],
        max_pages=5
    )
