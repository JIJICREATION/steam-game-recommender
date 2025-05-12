"""
- 환경변수를 이용해 MySQL DB에 연결 후, TITLELIST 테이블의 user_tags 컬럼 데이터를 로드
- 문자열 형태로 저장된 태그(user_tags)를 리스트로 변환하고 평탄화하여 모든 태그 추출
- 추출한 태그에서 None, 빈 문자열 및 "none"과 같은 무의미한 값을 제거하여 정제
- 최종 정제된 고유 태그에 대해 중복을 제거한 뒤 0부터 시작하는 정수 인덱스(tags_id)를 부여하고 DataFrame 구성
- 결과는 tag_results.log 파일에 UTF-8 형식으로 저장하여 로그로 기록

"""




import os
import ast
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경 변수 불러오기
host = os.getenv("host")
port = os.getenv("port")
dbuser = os.getenv("dbuser")
password = os.getenv("password")
dbname = os.getenv("name")

# DB 연결
connection_str = f"mysql+pymysql://{dbuser}:{password}@{host}:{port}/{dbname}"
engine = create_engine(connection_str)

# TITLELIST 테이블에서 user_tags 컬럼 추출
query = "SELECT user_tags FROM TITLELIST"
df = pd.read_sql(query, engine)

# user_tags 컬럼의 모든 값을 고유하게 가져오기 (원래는 리스트 형태의 문자열)
raw_tags = df['user_tags'].unique()

# 각 문자열을 파싱하여 리스트로 변환하고 평탄화
all_tags = []
for tag_str in raw_tags:
    try:
        # ast.literal_eval을 사용해 문자열을 리스트로 변환
        parsed = ast.literal_eval(tag_str)
        if isinstance(parsed, list):
            all_tags.extend(parsed)
        else:
            all_tags.append(tag_str)
    except Exception as e:
        # 파싱 실패 시 그대로 사용
        all_tags.append(tag_str)

# None, 빈 문자열, 혹은 "none" (대소문자 구분없이)인 경우만 제거하고 나머지는 모두 유지
all_tags = [tag for tag in all_tags 
            if tag is not None 
            and str(tag).strip() != "" 
            and str(tag).strip().lower() != "none"]

# 중복 제거 및 고유 태그 Series 생성
unique_tags = pd.Series(all_tags).drop_duplicates().reset_index(drop=True)

# 고유 태그에 대해 정수 인덱스(0부터 시작하는 ID)를 부여
df_unique = pd.DataFrame({
    'tags_id': unique_tags.index.astype('int64'),
    'tags_name': unique_tags
})

# 결과를 텍스트 파일에 기록 (UTF-8 인코딩)
log_file = "tag_results.log"
with open(log_file, "w", encoding="utf-8") as f:
    f.write("고유 태그 및 정수 인덱스 결과:\n")
    f.write(df_unique.to_string(index=False))

print(f"결과가 {log_file} 파일에 저장되었습니다.")
