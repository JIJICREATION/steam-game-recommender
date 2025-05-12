
#######################################################################################
# 이 코드는 MariaDB에서 `REVIEW` 테이블과 `LIST_OF_MODA_INDI` 테이블을 `app_id`를 기준으로 
# 조인하여 필요한 데이터를 가져오고, 그 결과를 CSV 파일로 저장하는 코드입니다.
#######################################################################################


import pandas as pd
from sqlalchemy import create_engine

# MariaDB 연결 설정 (사용자명, 비밀번호, 호스트, 포트, DB 이름을 적절히 수정)
engine = create_engine('mysql+pymysql://minsung:password@bootcampproject2t1steam.cdi60g8ggh0i.ap-southeast-2.rds.amazonaws.com:3306/steam_lit_project')

# SQL 쿼리
sql_query = """
SELECT r.app_id, r.review_text, r.sentiment_label,r.sentiment_score,l.userScore
FROM REVIEW r
JOIN LIST_OF_MODA_INDI l
  ON r.app_id = l.app_id;
"""

# SQL 쿼리 실행하여 DataFrame으로 가져오기
df = pd.read_sql(sql_query, engine)

# 결과 확인 (처리된 데이터프레임)
print(df.head())

# DataFrame을 CSV로 저장 (파일명: processed_reviews.csv)
df.to_csv('processed_reviews.csv', index=False)

print("Data has been successfully saved as 'processed_reviews.csv'.")
