
#########################################################################################################
# 이 스크립트는 Steam 게임의 리뷰를 수집하고, 이를 정제하여 감성 분석을 수행한 후, 결과를 MariaDB에 저장합니다.
#########################################################################################################

import requests
import re
import html  # for HTML entity unescaping
import pandas as pd
import time
from transformers import pipeline
import logging
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

# 로깅 설정: INFO 레벨로 주요 이벤트 기록
logging.basicConfig(level=logging.INFO)

# .env 파일에 저장된 DB 접속 정보 로드 (예: dbuser, password, host, port, name)
load_dotenv()

# 사용자 Agent 설정
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}


# 1. 제공된 APP ID 리스트 (DB에 있는 APP ID)
app_ids = [
    1310990, 572220, 360620, 1777280, 204300, 534780, 206500, 3027820, 922530, 744650,
    3316660, 3177210, 748940, 1049590, 428460, 1225790, 878380, 676580, 820480, 560550,
    2406870, 558100, 1198760, 605920, 2083450, 1986900, 1965620, 63200, 1608220, 3170880,
    1101030, 2840020, 336420, 1460550, 1682070, 1158320, 431250, 511800, 207230, 2359300,
    2185490, 1876950, 771060, 2469490, 1571030, 1092150, 265750, 3267430, 2018820, 2571350,
    1705410, 572520, 2416480, 2289930, 1101420, 1513740, 1134320, 649770, 263860, 1257550,
    377260, 377150, 1424420, 1991340, 1691370, 1534430, 1102370, 822710, 262750, 1590020,
    285580, 3021440, 731250, 1000280, 945610, 98900, 2494370, 492840, 794040, 743580,
    1787820, 2765500, 2460910, 2374620, 2291400, 1382870, 1331120, 838510, 1306840, 1729830,
    715810, 1241380, 2404950, 1831770, 274620, 996690, 688500, 3477920, 480500, 730710,
    1892900, 3025600, 803800, 1476000, 1835930, 310110, 469930, 877980, 2249550, 463250,
    348460, 766210, 2066460, 949830, 924960, 861050, 1415540, 319570, 3258370, 1198020,
    558720, 2297160, 1101980, 265770, 950780, 2444750, 981870, 628880, 3009300, 766930,
    935630, 802410, 1025560, 588480, 1037380, 1737910, 1416120, 3327160, 2702340, 2678790,
    961260, 736780, 537680, 497120, 2449640, 2144870, 1946470, 968190, 923780, 888420,
    3391260, 3217230, 3203530, 3097040, 3091240, 3086890, 2939730, 2791640, 2786380, 2742350,
    2718750, 2584160, 2556690, 2385510, 2353580, 2329790, 2230840, 2184560, 2096540, 1916790,
    1750450, 1715800, 1712720, 1656080, 1653930, 1599980, 1534640, 1352760, 1337250, 1086710,
    2437160, 690510, 263500, 446030, 440280, 331360, 914700, 468250, 585630, 467990,
    353130, 214190, 2842110, 577210, 1106750, 1383550, 1385460, 300040, 682790, 1328190,
    2329720, 207150, 815250, 602490, 1079650, 1217500
]
logging.info(f"제공된 APP ID 개수: {len(app_ids)}")


# 2. Steam 리뷰 API를 사용하여 리뷰 데이터 수집 (최대 60,000건)
def fetch_reviews_for_app(appid, max_reviews=1000):
    """Steam API에서 특정 게임(appid)의 최대 max_reviews 개수의 리뷰를 가져온다."""
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
                "review_id": review.get("recommendationid"),
                "review_text": review.get("review", ""),
                "timestamp": review.get("timestamp_created"),
                "steam_purchase": review.get("steam_purchase"),
                "playtime_forever": review.get("author", {}).get("playtime_forever"),
                "voted_up": review.get("voted_up")
            })
            if len(reviews) >= max_reviews:
                break
        
        cursor = data.get("cursor")
        if not cursor or cursor in seen_cursors:
            break
        seen_cursors.add(cursor)
        time.sleep(0.5)  # 요청 간 간격 조정
    return reviews

max_total_reviews = 60000
reviews_data = []

# 제공된 APP ID 리스트를 순회하며 리뷰 데이터 수집 (총 6만 건이 목표)
for appid in app_ids:
    if len(reviews_data) >= max_total_reviews:
        break
    # 각 APP ID에 대해 남은 건수를 목표로 리뷰를 가져옴
    remaining = max_total_reviews - len(reviews_data)
    logging.info(f"APP ID {appid}의 리뷰 수집 시작. 남은 리뷰 건수: {remaining}")
    reviews = fetch_reviews_for_app(appid, max_reviews=remaining)
    reviews_data.extend(reviews)
    logging.info(f"APP ID {appid} 수집 완료. 현재까지 수집된 리뷰 건수: {len(reviews_data)}")

logging.info(f"총 수집된 리뷰 수: {len(reviews_data)}")


# 3. 데이터 정제 (이모지, HTML 태그, 불필요한 공백 제거)
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

for review in reviews_data:
    review["review_text"] = clean_review_text(review["review_text"])


# 4. 감성 분석 (Positive / Negative)
sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

sentiment_labels = []
sentiment_scores = []

for review in reviews_data:
    # 리뷰 텍스트의 길이가 매우 긴 경우 앞쪽 512 토큰까지만 분석
    result = sentiment_pipeline(review["review_text"][:512])
    sentiment_labels.append(result[0]["label"])
    sentiment_scores.append(result[0]["score"])

# 감성 분석 결과 DataFrame에 추가
df_reviews = pd.DataFrame(reviews_data)
df_reviews["sentiment_label"] = sentiment_labels
df_reviews["sentiment_score"] = sentiment_scores

# timestamp와 review_id 컬럼 제거 (요청사항)
df_reviews.drop(columns=["review_id", "timestamp"], inplace=True)

# playtime_forever를 시간 단위로 변환 (분 -> 시간)
df_reviews["playtime_forever"] = (pd.to_numeric(df_reviews["playtime_forever"], errors='coerce') / 60).round(1)


# 5. MariaDB에 데이터 적재
dbuser = os.getenv("dbuser")
password = os.getenv("password")
host = os.getenv("host")
port = os.getenv("port")
name = os.getenv("name")

db_connection_str = f"mysql+pymysql://{dbuser}:{password}@{host}:{port}/{name}"
engine = create_engine(db_connection_str)

try:
    # "REVIEW" 테이블에 데이터 적재 (존재할 경우 append)
    df_reviews.to_sql("REVIEW", engine, if_exists="append", index=False)
    logging.info("MariaDB 적재 완료")
except Exception as e:
    logging.error(f"MariaDB 적재 중 오류 발생: {e}")
