

###################################################################################################
# 불용어 리스트 및 탑 키워드 수정중                                                                 
# 이 코드는 Steam 게임 리뷰 데이터를 읽어들이고, 각 리뷰에 대해 사용자가 직접                         
# 'top_keywords' (상위 3개 키워드)를 입력하도록 요구한 후, 결과를 CSV 파일로 저장                    
# 사용자는 각 리뷰에 대해 쉼표로 구분된 키워드 입력합                                                
# 불용어(stopwords) 리스트 관사 , 접속사 , 대명사 등 불피요한 단어는 일단 제외 나중에 더 추가할 예정
##################################################################################################import pymysql

import pymysql
import openai
# monkey-patch: openai.completions -> openai.Completion
openai.completions = openai.Completion

from keybert import KeyLLM
from keybert.llm import OpenAI as OpenAI_KLLM
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from collections import Counter
import pandas as pd

# 하드코딩된 DB 접속 정보
host = "bootcampproject2t1steam.cdi60g8ggh0i.ap-southeast-2.rds.amazonaws.com"
port = 3306
dbuser = "minsung"
password = "password"
name = "steam_lit_project"

# 하드코딩된 OpenAI API 키 및 CSV 출력 경로
OPENAI_API_KEY = "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"  # 본인의 API 키로 변경
CSV_OUTPUT_PATH = r"C:\Users\abwm2\Desktop\BootCamp\TIL\팀프로젝트 steam\J\keyword_frequencies.csv"

# 데이터베이스 연결 설정
db_config = {
    "host": host,
    "port": port,
    "user": dbuser,
    "password": password,
    "database": name,
    "charset": "utf8mb4"
}

# MariaDB에 연결 및 리뷰 데이터 추출 (테스트용으로 200건만)
try:
    connection = pymysql.connect(**db_config)
    with connection.cursor() as cursor:
        sql = "SELECT review_text FROM REVIEW LIMIT 50;"
        cursor.execute(sql)
        result = cursor.fetchall()
        # 각 튜플의 첫 번째 요소가 review_text
        reviews = [row[0] for row in result]
finally:
    connection.close()

print(f"총 {len(reviews)}개의 리뷰 데이터를 가져왔습니다.")

# OpenAI API 및 KEYLLM 초기화
openai.api_key = OPENAI_API_KEY
llm_client = OpenAI_KLLM(openai)
kw_model = KeyLLM(llm_client)

# 리뷰 데이터를 이용해 각 리뷰의 키워드를 추출 (리스트의 리스트 형태)
keywords_per_review = kw_model.extract_keywords(reviews)

# 기본 불용어 제거 (scikit-learn의 ENGLISH_STOP_WORDS 사용)
stop_words = set(word.lower() for word in ENGLISH_STOP_WORDS)
filtered_keywords_all = []
for kw_list in keywords_per_review:
    for kw in kw_list:
        if kw and kw.lower() not in stop_words:
            filtered_keywords_all.append(kw.strip())

# 키워드 빈도수 계산
keyword_counts = Counter(filtered_keywords_all)
print("전체 키워드 개수:", len(keyword_counts))

# DataFrame으로 변환하여 빈도수 내림차순 정렬
df_keywords = pd.DataFrame(keyword_counts.items(), columns=["Keyword", "Frequency"])
df_keywords.sort_values(by="Frequency", ascending=False, inplace=True)

# 상위 70% (빈도수가 높은 순으로 상위 70%에 해당하는 부분) 필터링
top_70_count = int(len(df_keywords) * 0.7)
df_top70 = df_keywords.iloc[:top_70_count]
print(f"전체 키워드 중 상위 70%에 해당하는 항목 수: {len(df_top70)}")

# 상위 70% 항목 중 상위 20개 선택
df_top20 = df_top70.head(20)
print("상위 20개 키워드:")
print(df_top20)

# CSV 파일로 저장 (여기서는 상위 20개만 저장)
df_top20.to_csv(CSV_OUTPUT_PATH, index=False)
print(f"상위 20개 키워드 결과가 CSV 파일로 저장되었습니다: {CSV_OUTPUT_PATH}")
