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

# MariaDB에서 app_id 가져오기
dbuser = os.getenv("dbuser")
password = os.getenv("password")
host = os.getenv("host")
port = os.getenv("port")
name = os.getenv("name")

# 데이터베이스 연결 문자열 (DB에서 app_id를 가져오기 위해 사용)
db_connection_str = f"mysql+pymysql://{dbuser}:{password}@{host}:{port}/{name}"
engine = create_engine(db_connection_str)

# SQL 쿼리 실행하여 app_id 가져오기
query = "SELECT app_id FROM LIST_OF_MODA_INDI"  # 예시: LIST_OF_MODA_INDI 테이블에서 app_id 가져오기
app_ids_from_db = pd.read_sql(query, engine)
app_ids = app_ids_from_db["app_id"].tolist()
logging.info(f"DB에서 가져온 APP ID 개수: {len(app_ids)}")


# 1. Steam 리뷰 API를 사용하여 리뷰 데이터 수집 (최대 60,000건)
def fetch_reviews_for_app(appid, max_reviews=10):
    """
    Steam API에서 특정 게임(appid)의 최대 max_reviews 개수의 리뷰를 가져온다.
    추가로 VOTES_UP, VOTED_UP, REVIEW_ID, WEIGHTED_COUNT 정보를 포함한다.
    """
    reviews = []
    cursor = "*"
    seen_cursors = set()
    
    url = f"https://store.steampowered.com/appreviews/{appid}"
    params = {
        "json": 1,
        "language": "english",     # 영어 리뷰만 가져오기
        "filter": "recent",        # 최신순 정렬
        "review_type": "all",      # 긍정 및 부정 리뷰 모두
        "purchase_type": "all",    # 모든 구매 유형 포함
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
                "review_id": review.get("recommendationid"),      # REVIEW_ID
                "review_text": review.get("review", ""),
                "timestamp": review.get("timestamp_created"),
                "steam_purchase": review.get("steam_purchase"),
                "playtime_forever": review.get("author", {}).get("playtime_forever"),
                "voted_up": review.get("voted_up"),                 # VOTED_UP (Boolean)
                "votes_up": review.get("votes_up"),                 # VOTES_UP (추천 수)
                "weighted_count": review.get("weighted_vote_score")   # WEIGHTED_COUNT
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
    """
    리뷰 텍스트에서 이모지, HTML 태그, BBCode, 불필요한 공백을 제거한다.
    """
    text = emoji_pattern.sub('', text)
    text = html_tag_pattern.sub('', text)
    text = bbcode_pattern.sub('', text)
    text = html.unescape(text)
    text = re.sub(r'[^A-Za-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# 3. 감성 분석 부분 제거 및 리뷰 데이터 수집 후 전처리
reviews_data = []  # 각 앱의 리뷰 데이터를 담을 리스트

# 테스트용으로 총 100개의 리뷰만 수집하도록 제한
MAX_TOTAL_REVIEWS = 100

for appid in app_ids:
    logging.info(f"APP ID {appid}의 리뷰 수집 중...")
    reviews = fetch_reviews_for_app(appid, max_reviews=10)  # 앱당 최대 10건씩 수집
    for review in reviews:
        review["review_text"] = clean_review_text(review["review_text"])
        reviews_data.append(review)
        if len(reviews_data) >= MAX_TOTAL_REVIEWS:
            break
    if len(reviews_data) >= MAX_TOTAL_REVIEWS:
        break

logging.info(f"총 {len(reviews_data)}개의 리뷰 데이터를 수집했습니다.")

# 4. DataFrame 생성 및 후처리
df_reviews = pd.DataFrame(reviews_data)

# playtime_forever를 분 단위에서 시간 단위로 변환 (소수점 1자리)
df_reviews["playtime_forever"] = (pd.to_numeric(df_reviews["playtime_forever"], errors='coerce') / 60).round(1)

# 5. CSV 파일로 저장 (DB 적재 없이 CSV로 저장)
output_csv = "reviews_with_genres.csv"
df_reviews.to_csv(output_csv, index=False, encoding="utf-8")
logging.info(f"CSV 파일로 저장 완료: {output_csv}")
