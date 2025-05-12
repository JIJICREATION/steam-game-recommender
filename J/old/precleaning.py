import os
import requests
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
load_dotenv()
# .env에서 DB 연결 정보를 가져옵니다.
dbuser = os.getenv('dbuser')
password = os.getenv('password')
host = os.getenv('host')
port = os.getenv('port')
name = os.getenv('name')

# app_id  ID 목록 (도타2 / CS:GO / PUBG)
app_ids = [570, 730, 578080]
all_reviews = []  # 모든 리뷰 데이터를 저장할 리스트

# 리뷰 개수 제한
num_reviews_limit = 20

# 1. 각 앱 ID에 대해 리뷰 데이터 호출
for app_id in app_ids:
    # 리뷰 API URL: 각 앱별로 호출합니다.
    api_url = f"https://store.steampowered.com/appreviews/{app_id}?json=1&num_per_page={num_reviews_limit}"
    response = requests.get(api_url)
    if response.status_code == 200:
        data_json = response.json()
        # 반환된 JSON 구조: {"query_summary": {...}, "reviews": [ {...}, {...}, ... ]}
        reviews = data_json.get("reviews", [])
        if not reviews:
            print(f"앱 ID {app_id}에 대해 리뷰 데이터가 없습니다.")
        for review in reviews:
            extracted = {
                "review_id": review.get("recommendationid"),
                "timestamp": review.get("timestamp_created"),  # UNIX timestamp
                "playtime_forever": review.get("author", {}).get("playtime_forever")
            }
            all_reviews.append(extracted)
            
# 2. 추출한 리뷰 데이터를 DataFrame으로 변환
df_reviews = pd.DataFrame(all_reviews)
print("전처리 전 리뷰 데이터:")
print(df_reviews.head())
# 전처리 및 클렌징
df_reviews.dropna(inplace=True)
# timestamp 컬럼을 datetime 형식으로 변환 (UNIX timestamp 기준)
if "timestamp" in df_reviews.columns:
    df_reviews["timestamp"] = pd.to_datetime(df_reviews["timestamp"], unit='s')

# playtime_forever 컬럼을 숫자형으로 변환
if "playtime_forever" in df_reviews.columns:
    df_reviews["playtime_forever"] = pd.to_numeric(df_reviews["playtime_forever"], errors='coerce')

print("전처리된 리뷰 데이터:")
print(df_reviews.head())

# 3. MariaDB 적재
db_connection_str = f'mysql+pymysql://{dbuser}:{password}@{host}:{port}/{name}'
print("연결 문자열:", db_connection_str)
engine = create_engine(db_connection_str)
df_reviews.to_sql('target_table', engine, if_exists='append', index=False)
print("완료")
