import requests
import re
import html  # for HTML entity unescaping
import pandas as pd
import time
from transformers import pipeline
import logging
from dotenv import load_dotenv
import os

# 로깅 설정: INFO 레벨로 주요 이벤트 기록
logging.basicConfig(level=logging.INFO)

# .env 파일에 저장된 설정 로드 (필요한 경우)
load_dotenv()

# 사용자 Agent 설정
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

#########################################
# 1. 게임 ID 자동 수집 (Steam Store API 활용)
#########################################
def get_appids_by_tag(tag_id, start=0, count=100):
    """
    Steam Store API를 사용하여 특정 태그(tag_id)가 포함된 게임의 app_id 리스트를 가져온다.
    :param tag_id: Steam 태그 ID (예: 113: MOBA, 492: Indie)
    :param start: 검색 결과 시작 인덱스
    :param count: 한 번에 가져올 게임 수
    :return: 정수형 app_id 리스트
    """
    search_url = f"https://store.steampowered.com/search/render/?infinite=1&start={start}&count={count}&category1=998&tags={tag_id}&cc=US&l=english"
    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        search_data = response.json()
    except Exception as e:
        logging.error(f"태그 {tag_id}에 대한 게임 ID 가져오기 실패: {e}")
        return []
    
    results_html = search_data.get("results_html", "")
    found_appids = re.findall(r'/app/(\d+)', results_html)
    appids = list(set(map(int, found_appids)))
    return appids

# MOBA와 Indie 태그로 각각 게임 ID를 수집
moba_appids = get_appids_by_tag(113, start=0, count=100)
indie_appids = get_appids_by_tag(492, start=0, count=100)
logging.info(f"MOBA 게임 ID 개수: {len(moba_appids)}, Indie 게임 ID 개수: {len(indie_appids)}")

# 두 태그의 합집합: 두 태그에 해당하는 모든 게임의 app_id (중복 제거)
all_app_ids = list(set(moba_appids) | set(indie_appids))
logging.info(f"전체 게임 ID 개수 (합집합): {len(all_app_ids)}")

#########################################
# 2. Steam 리뷰 API를 사용하여 리뷰 데이터 수집 (총 약 60,000건 목표)
#########################################
def fetch_reviews_for_app(appid, max_reviews=200):
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
        response = requests.get(url, params=params)
        if response.status_code != 200:
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

reviews_data = []
max_total_reviews = 10000  # 총 60,000건 리뷰 수집 목표

# 모든 게임 ID(합집합)에 대해 리뷰 수집 (각 게임당 최대 200개)
for appid in all_app_ids:
    reviews = fetch_reviews_for_app(appid, max_reviews=200)
    reviews_data.extend(reviews)
    logging.info(f"App ID {appid}에서 {len(reviews)}개의 리뷰 수집")
    if len(reviews_data) >= max_total_reviews:
        logging.info(f"총 수집 리뷰 수가 {max_total_reviews}건에 도달하여 중단합니다.")
        break
    time.sleep(0.5)

logging.info(f"총 수집된 리뷰 수: {len(reviews_data)}")

#########################################
# 3. 데이터 정제 (이모지, HTML 태그, 불필요한 공백 제거)
#########################################
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

#########################################
# 4. 감성 분석 (Positive / Negative)
#########################################
sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

sentiment_labels = []
sentiment_scores = []

for review in reviews_data:
    result = sentiment_pipeline(review["review_text"][:512])
    sentiment_labels.append(result[0]["label"])
    sentiment_scores.append(result[0]["score"])

# 감성 분석 결과를 데이터프레임에 추가
df_reviews = pd.DataFrame(reviews_data)
df_reviews["sentiment_label"] = sentiment_labels
df_reviews["sentiment_score"] = sentiment_scores

# timestamp와 review_id 컬럼 제거 (요청사항)
df_reviews.drop(columns=["review_id", "timestamp"], inplace=True)

# playtime_forever를 시간 단위로 변환 (분 -> 시간)
df_reviews["playtime_forever"] = (pd.to_numeric(df_reviews["playtime_forever"], errors='coerce') / 60).round(1)

#########################################
# 5. 결과를 CSV 파일로 저장
#########################################
output_csv = r"C:\Users\abwm2\Desktop\BootCamp\TIL\팀프로젝트 steam\J\steam_reviews.csv"
df_reviews.to_csv(output_csv, index=False, encoding='utf-8-sig')
logging.info(f"결과가 '{output_csv}' 파일로 저장되었습니다.")
