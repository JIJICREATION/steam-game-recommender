import pandas as pd
from sqlalchemy import create_engine
from keybert import KeyBERT
import re

# 데이터베이스 연결 설정
# 'username', 'password', 'host', 'port', 'review_db', 'list_moda_db'는 실제 연결 정보로 대체해야 합니다.
engine_review = create_engine('mysql+pymysql://username:password@host:port/REVIEW_DB')
engine_list_moda = create_engine('mysql+pymysql://username:password@host:port/list_moda_db')

# 각 데이터베이스에서 데이터 불러오기
review_query = "SELECT app_id, review_text FROM review;"  # review 테이블의 app_id와 review_text를 불러옵니다.
list_moda_query = "SELECT app_id, other_column FROM list_moda_indi;"  # list_moda_indi 테이블에서 app_id와 다른 컬럼을 불러옵니다.

# 데이터프레임으로 읽어오기
review_df = pd.read_sql(review_query, engine_review)
list_moda_df = pd.read_sql(list_moda_query, engine_list_moda)

# app_id를 기준으로 데이터 병합 (inner join)
merged_df = pd.merge(review_df, list_moda_df, on='app_id', how='inner')

# 텍스트 전처리 함수 정의
def clean_text(text):
    text = text.lower()  # 소문자화
    text = re.sub(r'\s+', ' ', text)  # 여러 공백을 하나로
    text = re.sub(r'[^\w\s]', '', text)  # 특수문자 제거
    return text

# 'review_text' 컬럼을 전처리하여 'cleaned_review_text' 컬럼에 저장
merged_df['cleaned_review_text'] = merged_df['review_text'].apply(clean_text)

# Key-BERT 모델 로드
kw_model = KeyBERT()

# 각 리뷰에서 키워드 추출 함수 정의
def extract_keywords(text):
    keywords = kw_model.extract_keywords(text, top_n=5)  # 상위 5개 키워드 추출
    return [keyword[0] for keyword in keywords]

# 'cleaned_review_text' 컬럼에서 키워드를 추출하여 'keywords' 컬럼에 저장
merged_df['keywords'] = merged_df['cleaned_review_text'].apply(extract_keywords)

# 결과를 CSV 파일로 저장 (옵션)
merged_df.to_csv('merged_reviews_with_keywords.csv', index=False)

# 결과 출력 (선택사항)
print(merged_df[['app_id', 'keywords']].head())  # app_id와 키워드만 출력
