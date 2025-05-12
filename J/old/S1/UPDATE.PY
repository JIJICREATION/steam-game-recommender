import requests
import re
import html  # HTML 엔티티 변환용
import pandas as pd
import time
import logging
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

# 로깅 설정: INFO 레벨
logging.basicConfig(level=logging.INFO)

# .env 파일에 저장된 DB 접속 정보 로드 (예: dbuser, password, host, port, name)
load_dotenv()

# 사용자 Agent 설정
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# MariaDB 접속 정보
dbuser = os.getenv("dbuser")
password = os.getenv("password")
host = os.getenv("host")
port = os.getenv("port")
name = os.getenv("name")

# 데이터베이스 연결 문자열
db_connection_str = f"mysql+pymysql://{dbuser}:{password}@{host}:{port}/{name}"
engine = create_engine(db_connection_str)

# SQL 쿼리 실행하여 app_id 가져오기
query = "SELECT app_id FROM LIST_OF_MOBA_INDI"
app_ids_from_db = pd.read_sql(query, engine)
app_ids = app_ids_from_db["app_id"].tolist()
logging.info(f"DB에서 가져온 APP ID 개수: {len(app_ids)}")

# Steam 리뷰 API에서 데이터 수집

def fetch_reviews_for_app(appid, max_reviews=1000):
    reviews = []
    cursor = "*"
    seen_cursors = set()

    url = f"https://store.steampowered.com/appreviews/{appid}"
    params = {
        "json": 1,
        "language": "english",
        "filter": "recent",
        "review_type": "all",
        "purchase_type": "all",
        "num_per_page": 100,
        "cursor": cursor
    }

    while len(reviews) < max_reviews:
        params["cursor"] = cursor
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
        except Exception as e:
            logging.error(f"APP ID {appid}의 리뷰 가져오기 실패: {e}")
            break

        data = response.json()
        new_reviews = data.get("reviews", [])
        if not new_reviews:
            break

        for review in new_reviews:
            review_text = review.get("review", "").strip()
            if len(review_text.split()) > 3:  # 최소 4단어 이상인 리뷰만 의미있는 리뷰로 간주
                reviews.append({
                    "app_id": appid,
                    "review_id": review.get("recommendationid"),
                    "review_text": review_text,
                    "timestamp": review.get("timestamp_created"),
                    "steam_purchase": review.get("steam_purchase"),
                    "playtime_forever": review.get("author", {}).get("playtime_forever"),
                    "voted_up": review.get("voted_up"),
                    "votes_up": review.get("votes_up"),
                    "weighted_vote_score": review.get("weighted_vote_score"),
                })
            if len(reviews) >= max_reviews:
                break

        cursor = data.get("cursor")
        if not cursor or cursor in seen_cursors:
            break
        seen_cursors.add(cursor)
        time.sleep(0.5)

    return reviews

# 데이터 정제 (이모지, HTML 태그, 불필요한 공백 제거)
emoji_pattern = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\u2600-\u26FF"
    "\u2700-\u27BF"
    "]+", flags=re.UNICODE
)
html_tag_pattern = re.compile(r'<[^>]+>')
bbcode_pattern = re.compile(r'\[/?\w+.*?\]')

def clean_review_text(text):
    text = emoji_pattern.sub('', text)
    text = html_tag_pattern.sub('', text)
    text = bbcode_pattern.sub('', text)
    text = html.unescape(text)
    text = re.sub(r'[^A-Za-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

reviews_data = []

for appid in app_ids:
    logging.info(f"APP ID {appid}의 리뷰 수집 중...")
    reviews = fetch_reviews_for_app(appid, max_reviews=1000)
    for review in reviews:
        review["review_text"] = clean_review_text(review["review_text"])
        reviews_data.append(review)

logging.info(f"총 {len(reviews_data)}개의 리뷰 데이터를 수집했습니다.")

df_reviews = pd.DataFrame(reviews_data)
df_reviews["playtime_forever"] = (pd.to_numeric(df_reviews["playtime_forever"], errors='coerce') / 60).round(1)
df_reviews["timestamp"] = pd.to_datetime(df_reviews["timestamp"], unit='s')

df_reviews.to_sql("GAME_REVIEW", engine, if_exists="replace", index=False)
logging.info("DB 적재 완료: GAME_REVIEW 테이블에 저장됨.")
