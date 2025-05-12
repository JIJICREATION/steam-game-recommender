


"""
이 스크립트는 데이터베이스에서 게임(app) ID를 읽어와 Steam 리뷰 API를 통해 각 게임의 리뷰 데이터를 수집, 전처리하고,
최종적으로 MariaDB의 GAME_REVIEW 테이블에 저장하는 ETL 파이프라인을 구현합니다.

주요 기능:
1. 환경 변수(.env)에서 DB 접속 정보를 로드하고, MariaDB에 연결.
2. 데이터베이스에서 app_id 목록을 조회.
3. 각 app_id에 대해 Steam 리뷰 API를 호출하여 최대 지정 개수만큼 리뷰(추천 여부, 추천 받은 횟수 등 포함)를 수집.
4. 수집한 리뷰 텍스트에서 이모지, HTML 태그, BBCode, 특수문자 및 불필요한 공백을 제거하는 전처리 수행.
5. 리뷰 데이터의 playtime을 시간 단위로 변환하고, Unix 타임스탬프를 datetime 형식으로 변경.
6. 최종적으로 정제된 데이터를 GAME_REVIEW 테이블에 적재.

"""




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
query = "SELECT app_id FROM LIST_OF_MODA_INDI"
app_ids_from_db = pd.read_sql(query, engine)
app_ids = app_ids_from_db["app_id"].tolist()
logging.info(f"DB에서 가져온 APP ID 개수: {len(app_ids)}")


# 1. Steam 리뷰 API에서 데이터 수집 (votes_up 포함)
def fetch_reviews_for_app(appid, max_reviews=60000):
    """
    Steam API에서 특정 게임(appid)의 최대 max_reviews 개수의 리뷰를 가져온다.
    여기서는 review_id, review_text, timestamp, steam_purchase,
    playtime_forever, voted_up, votes_up 등의 필드를 포함한다.
    """
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
            reviews.append({
                "app_id": appid,
                "review_id": review.get("recommendationid"),
                "review_text": review.get("review", ""),
                "timestamp": review.get("timestamp_created"),
                "steam_purchase": review.get("steam_purchase"),
                "playtime_forever": review.get("author", {}).get("playtime_forever"),
                "voted_up": review.get("voted_up"),  # 추천 여부 (True / False)
                "votes_up": review.get("votes_up"),   # 추천 받은 총 횟수
                "weighted_vote_score": review.get("weighted_vote_score"),
        })
            if len(reviews) >= max_reviews:
                break
        
        cursor = data.get("cursor")
        if not cursor or cursor in seen_cursors:
            break
        seen_cursors.add(cursor)
        time.sleep(0.5)  # 요청 간 간격 조정
    return reviews


# 2. 데이터 정제 (이모지, HTML 태그, 불필요한 공백 제거)
emoji_pattern = re.compile(
    "[" 
    "\U0001F600-\U0001F64F"  # 이모티콘
    "\U0001F300-\U0001F5FF"  # 그림문자
    "\U0001F680-\U0001F6FF"  # 지도 기호
    "\U0001F1E0-\U0001F1FF"  # 국기 기호
    "\u2600-\u26FF"          # 기타 기호
    "\u2700-\u27BF"          # 딩배트 기호
    "]+", flags=re.UNICODE
)
html_tag_pattern = re.compile(r'<[^>]+>')
bbcode_pattern = re.compile(r'\[/?\w+.*?\]')

def clean_review_text(text):
    """리뷰 텍스트에서 이모지, HTML 태그, BBCode, 그리고 불필요한 공백을 제거한다."""
    text = emoji_pattern.sub('', text)
    text = html_tag_pattern.sub('', text)
    text = bbcode_pattern.sub('', text)
    text = html.unescape(text)
    text = re.sub(r'[^A-Za-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# 3. 감성 분석 제거 후, 리뷰 데이터 수집 및 전처리
reviews_data = []  # 각 앱의 리뷰 데이터를 담을 리스트

for appid in app_ids:
    logging.info(f"APP ID {appid}의 리뷰 수집 중...")
    reviews = fetch_reviews_for_app(appid, max_reviews=60000)
    for review in reviews:
        review["review_text"] = clean_review_text(review["review_text"])
        reviews_data.append(review)

logging.info(f"총 {len(reviews_data)}개의 리뷰 데이터를 수집했습니다.")

# 리뷰 데이터 DataFrame 생성
df_reviews = pd.DataFrame(reviews_data)

# playtime_forever를 분 단위에서 시간 단위로 변환 (소수점 1자리)
df_reviews["playtime_forever"] = (pd.to_numeric(df_reviews["playtime_forever"], errors='coerce') / 60).round(1)

# timestamp 변환: Unix 타임스탬프(초)를 datetime 형식으로 변환 (예: YYYY-MM-DD HH:MM:SS)
df_reviews["timestamp"] = pd.to_datetime(df_reviews["timestamp"], unit='s')

# 4. DB 적재: GAME_REVIEW 테이블에 저장 (기존 테이블 있으면 덮어쓰기)
df_reviews.to_sql("GAME_REVIEW", engine, if_exists="replace", index=False)
logging.info("DB 적재 완료: GAME_REVIEW 테이블에 저장됨.")
