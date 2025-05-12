import requests
import re
import html  # for HTML entity unescaping
import pandas as pd
import time
from transformers import pipeline
import logging
from dotenv import load_dotenv
from keybert import KeyBERT

# NLTK 관련 임포트 및 WordNet 다운로드 (최초 1회 실행)
import nltk
nltk.download('wordnet')
nltk.download('omw-1.4')
from nltk.corpus import wordnet

# 동의어(유의어)를 가져오는 함수
def get_synonyms(word):
    """
    주어진 단어(word)에 대해 WordNet을 사용해 동의어 리스트를 반환합니다.
    """
    synonyms = set()
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            # 동의어 단어에 포함된 언더스코어(_)를 공백으로 바꿔줍니다.
            synonyms.add(lemma.name().replace('_', ' '))
    return list(synonyms)

# 로깅 설정: INFO 레벨로 주요 이벤트 기록
logging.basicConfig(level=logging.INFO)

# .env 파일에 저장된 설정 로드 (필요한 경우 사용)
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
    :param tag_id: Steam 태그 ID (예: 113: MOBA, 1775: Indie)
    :param start: 검색 결과 시작 인덱스
    :param count: 가져올 게임 수 (한 번에)
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

# MOBA 및 Indie 장르의 게임 ID를 자동으로 가져오기
moba_appids = get_appids_by_tag(113, start=0, count=100)
indie_appids = get_appids_by_tag(1775, start=0, count=100)
app_ids = moba_appids + indie_appids
logging.info(f"MOBA 게임 ID 개수: {len(moba_appids)}, Indie 게임 ID 개수: {len(indie_appids)}")
logging.info(f"전체 게임 ID 개수: {len(app_ids)}")

#########################################
# 2. Steam 리뷰 API를 사용하여 리뷰 데이터 수집 (최대 약 10,000건)
#########################################
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

# 최대 10,000건 리뷰 수집 (각 장르에서 대략 절반씩)
max_total_reviews = 10000
target_per_genre = max_total_reviews // 2
reviews_data = []

# MOBA 리뷰 수집
for appid in moba_appids:
    if len(reviews_data) >= target_per_genre:
        break
    reviews = fetch_reviews_for_app(appid, max_reviews=target_per_genre - len(reviews_data))
    reviews_data.extend(reviews)

# Indie 리뷰 수집
for appid in indie_appids:
    if len(reviews_data) >= max_total_reviews:
        break
    reviews = fetch_reviews_for_app(appid, max_reviews=max_total_reviews - len(reviews_data))
    reviews_data.extend(reviews)

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
    # 리뷰 텍스트가 비어있을 경우 예외 처리
    text = review["review_text"] if review["review_text"] else "No review text"
    result = sentiment_pipeline(text[:512])
    sentiment_labels.append(result[0]["label"])
    sentiment_scores.append(result[0]["score"])

# 감성 분석 결과를 reviews_data에 추가하고 DataFrame 생성
for i, review in enumerate(reviews_data):
    review["sentiment_label"] = sentiment_labels[i]
    review["sentiment_score"] = sentiment_scores[i]

df_reviews = pd.DataFrame(reviews_data)

# timestamp와 review_id 컬럼 제거 (요청사항)
df_reviews.drop(columns=["review_id", "timestamp"], inplace=True)

# playtime_forever를 시간 단위로 변환 (분 -> 시간)
df_reviews["playtime_forever"] = (pd.to_numeric(df_reviews["playtime_forever"], errors='coerce') / 60).round(1)

#########################################
# 5. KEYBERT를 사용한 키워드와 문서 간 유사도 계산 (터미널 출력)
#########################################
# 기본 후보 키워드 목록 (리뷰 도메인에 맞게 필요에 따라 수정)
candidate_keywords = [
    "GOAT","fun", "hackers","sentiment", "purchase", "positive", "negative", "Steam"
]

# 동의어(유의어) 처리: 각 후보 단어에 대해 동의어를 확장합니다.
expanded_candidates = set(candidate_keywords)
for word in candidate_keywords:
    synonyms = get_synonyms(word)
    expanded_candidates.update(synonyms)

# 최종 후보 키워드 리스트 (중복 제거됨)
expanded_candidates = list(expanded_candidates)
print("동의어 확장이 적용된 후보 키워드:")
print(expanded_candidates)

# 분석할 문서 선택: 여기서는 첫 번째 리뷰 텍스트를 예시로 사용
if not df_reviews.empty:
    sample_doc = df_reviews.iloc[0]['review_text']
else:
    sample_doc = "리뷰 데이터가 없습니다."

# KEYBERT 모델 초기화 (예: all-MiniLM-L6-v2 모델 사용)
kw_model = KeyBERT("all-MiniLM-L6-v2")

# 후보 키워드를 사용하여 문서와 각 키워드 간의 유사도 계산
results = kw_model.extract_keywords(
    sample_doc,
    keyphrase_ngram_range=(1, 1),
    candidates=expanded_candidates,
    top_n=10
)

print("선택된 문서와 후보 키워드 간의 유사도 결과:")
for keyword, score in results:
    print(f"키워드: {keyword}  -  유사도: {score:.4f}")
