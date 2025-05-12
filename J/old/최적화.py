import os
import requests
import pandas as pd
from dotenv import load_dotenv
from transformers import pipeline
import logging

# 로그 설정: INFO 레벨로 설정하여 실행 중 주요 이벤트를 기록합니다.
logging.basicConfig(level=logging.INFO)

def run_pipeline():
    # .env 파일에 저장된 환경변수를 로드합니다.
    load_dotenv()

    # 분석할 앱 ID 장르 (moba) (인디)
    app_ids = [113,1775]
    all_reviews = []  # 모든 리뷰 데이터를 저장할 리스트

    # 각 앱 당 리뷰 개수 제한 (예시에서는 20개)
    num_reviews_limit = 10

    # Hugging Face의 감성 분석 파이프라인을 초기화
    sentiment_analyzer = pipeline("sentiment-analysis")

    # 각 앱 ID에 대해 리뷰 데이터를 호출하고, NLP 처리를 진행
    for app_id in app_ids:
        logging.info(f"앱 ID {app_id}의 리뷰 데이터를 수집.")
        api_url = f"https://store.steampowered.com/appreviews/{app_id}?json=1&num_per_page={num_reviews_limit}"
        response = requests.get(api_url)
        if response.status_code == 200:
            data_json = response.json()
            reviews = data_json.get("reviews", [])
            if not reviews:
                logging.warning(f"앱 ID {app_id}에 대해 리뷰 데이터가 없습니다.")
            for review in reviews:
                # 리뷰 텍스트를 추출 (API의 JSON 구조에 따라 'review' 키 사용)
                review_text = review.get("review", "")
                
                # NLP 감성 분석: 리뷰 텍스트가 존재하면 분석을 수행합니다.
                if review_text:
                    sentiment_result = sentiment_analyzer(review_text)
                    sentiment = sentiment_result[0]["label"] if sentiment_result else None
                else:
                    sentiment = None

                # 필요한 정보를 추출하여 딕셔너리 형태로 저장합니다.
                extracted = {
                    "review_id": review.get("recommendationid"),
                    "timestamp": review.get("timestamp_created"),
                    "playtime_forever": review.get("author", {}).get("playtime_forever"),
                    "review_text": review_text,
                    "sentiment": sentiment
                }
                all_reviews.append(extracted)
        else:
            logging.error(f"앱 ID {app_id}의 데이터 호출 실패: 상태 코드 {response.status_code}")

    # 추출한 리뷰 데이터를 DataFrame으로 변환합니다.
    df_reviews = pd.DataFrame(all_reviews)
    logging.info("전처리 전 리뷰 데이터 샘플:")
    logging.info(df_reviews.head())
    
    # 데이터 클렌징: 결측치 제거
    df_reviews.dropna(inplace=True)
    
    # timestamp 컬럼을 datetime 형식으로 변환 (UNIX timestamp 기준)
    if "timestamp" in df_reviews.columns:
        df_reviews["timestamp"] = pd.to_datetime(df_reviews["timestamp"], unit='s')
    
    # playtime_forever 컬럼을 숫자형으로 변환 (오류 발생 시 NaN 처리)
    if "playtime_forever" in df_reviews.columns:
        df_reviews["playtime_forever"] = pd.to_numeric(df_reviews["playtime_forever"], errors='coerce')
    
    logging.info("전처리 후 리뷰 데이터 샘플:")
    logging.info(df_reviews.head())

    # 결과 출력: DataFrame을 콘솔에 출력합니다.
    print(df_reviews)

if __name__ == '__main__':
    run_pipeline()
