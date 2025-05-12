'''
review_text에 대해서 LLM을 통해 키워드를 추출 하는 모듈입니다. 
db로 변경될 필요가 있습니다. 

'''

import pandas as pd
from keybert import KeyLLM
from keybert.llm import OpenAI
from dotenv import load_dotenv
import openai
import os

# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI API 키 확인
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

# OpenAI 클라이언트 초기화
client = openai.OpenAI(api_key=openai_api_key)  # `client` 객체 생성
llm = OpenAI(client)  # `client`를 인수로 전달

# KeyLLM 모델 초기화
kw_model = KeyLLM(llm)

# CSV 파일 읽기
df = pd.read_csv('D:/T1/top70_reviews.csv')

# 키워드 추출 함수
def extract_keywords(text):
<<<<<<< HEAD
    keywords = kw_model.extract_keywords(text)
    return keywords

# 리뷰 텍스트에서 키워드 추출
df['keyLLM_keywords'] = df['keywords'].apply(extract_keywords)
=======
    """10자 이상의 리뷰 텍스트에 대해서만 키워드 추출"""
    if pd.isna(text) or len(str(text).strip()) < 10:
        return []
    return kw_model.extract_keywords(text)

# 조건부 키워드 추출 적용
df['keyLLM_keywords'] = df['review_text'].apply(
    lambda x: extract_keywords(x) if len(str(x)) >= 10 else []
)

>>>>>>> bb5fe532052a65568f5396c5279c58effc69f8cc

# 결과 출력
print(df[['review_text', 'keyLLM_keywords']])

# 결과를 CSV 파일로 저장
<<<<<<< HEAD
df.to_csv('D:/T1/reviews_key_bert_keyllm_keywords.csv', index=False)
=======
df.to_csv('D:/T1/reviews_keyllm_keywords.csv', index=False)
>>>>>>> bb5fe532052a65568f5396c5279c58effc69f8cc
