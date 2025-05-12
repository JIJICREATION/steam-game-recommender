import pandas as pd
import requests
import re
from sqlalchemy import create_engine, text

def fetch_steam_reviews(app_id, max_reviews=100):
    """
    Steam Store API를 사용하여 특정 app_id의 리뷰를 최대 max_reviews개 가져와 DataFrame으로 반환합니다.
    """
    reviews_list = []
    cursor = '*'
    fetched = 0
    # Steam 리뷰 API: 한 번에 최대 100개씩 가져올 수 있으므로 반복 호출하여 max_reviews만큼 수집
    while fetched < max_reviews:
        url = (
            f"https://store.steampowered.com/appreviews/{app_id}?json=1"
            f"&num_per_page=100&cursor={cursor}&purchase_type=all&language=all"
        )
        response = requests.get(url)
        data = response.json()
        if 'reviews' not in data:
            break  # 데이터가 없으면 종료
        for review in data['reviews']:
            # 필요한 필드 추출
            review_id = review.get('recommendationid')
            review_text = review.get('review')
            timestamp = review.get('timestamp_created')
            playtime = review.get('author', {}).get('playtime_forever')
            voted_up = review.get('voted_up')  # True/False 값
            # 필수 필드가 존재하는 리뷰만 처리
            if review_id and review_text and timestamp is not None and playtime is not None:
                reviews_list.append({
                    'review_id': review_id,
                    'review_text': review_text,
                    'timestamp': timestamp,
                    'playtime_forever': playtime,
                    'app_id': app_id,
                    'sentiment_label': 'positive' if voted_up else 'negative'
                })
            fetched += 1
            if fetched >= max_reviews:
                break
        # 다음 페이지의 cursor 갱신 (Steam API가 제공하는 cursor 이용)
        cursor = data.get('cursor')
        if not cursor or cursor == "false":
            break  # 더 가져올 리뷰가 없으면 종료
    # DataFrame 생성
    df_reviews = pd.DataFrame(reviews_list)
    return df_reviews

# 사용 예시: app_id 570 (Dota 2)의 최신 리뷰 200개 수집
df = fetch_steam_reviews(app_id=570, max_reviews=200)
print(f"가져온 리뷰 개수: {len(df)}")
print(df.head(3))
