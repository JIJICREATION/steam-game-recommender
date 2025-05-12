import os
import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics.pairwise import cosine_similarity
import ast

# 환경 변수나 설정 파일에서 민감 정보를 주입받는 것이 이상적이나, 여기서는 예시를 위해 하드 코딩합니다.
db_host = "bootcampproject2t1steam.cdi60g8ggh0i.ap-southeast-2.rds.amazonaws.com"
db_port = 3306
db_user = "minsung"
db_password = "password"
db_name = "steam_lit_project"

connection_string = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
engine = create_engine(connection_string, pool_pre_ping=True)

def fetch_all_similar_games(engine):
    """
    SIMILAR_GAMES 테이블의 전체 데이터를 조회하는 함수.
    """
    query = text("""
        SELECT game_app_id, recommended_app_id, recommended_title, user_tags
        FROM SIMILAR_GAMES
    """)
    with engine.connect() as connection:
        df = pd.read_sql(query, connection)
    return df

# SIMILAR_GAMES 테이블의 전체 데이터를 불러옵니다.
data_df = fetch_all_similar_games(engine)

def parse_tags(tag_field):
    """
    user_tags 컬럼이 문자열인 경우 안전하게 리스트로 변환합니다.
    """
    if isinstance(tag_field, str):
        try:
            return ast.literal_eval(tag_field)
        except Exception:
            return []
    elif isinstance(tag_field, list):
        return tag_field
    else:
        return []

# user_tags 컬럼 파싱
data_df['user_tags'] = data_df['user_tags'].apply(parse_tags)

# 태그 벡터화: MultiLabelBinarizer를 사용해 전체 데이터의 태그를 이진 벡터화합니다.
mlb = MultiLabelBinarizer()
tag_matrix = mlb.fit_transform(data_df['user_tags'])

# 코사인 유사도 계산 (각 추천 항목 간의 유사도를 계산)
cos_sim = cosine_similarity(tag_matrix)

# 추천 제목(recommended_title)을 인덱스 및 컬럼으로 사용하여 유사도 DataFrame 생성
similarity_df = pd.DataFrame(cos_sim,
                             index=data_df['recommended_title'],
                             columns=data_df['recommended_title'])
print(similarity_df)

# CSV 파일 대신, similarity_df를 새로운 DB 테이블(예: 'similarity_matrix')에 적재합니다.
# if_exists='replace'는 테이블이 이미 있으면 덮어쓰기를 의미합니다.
similarity_df.to_sql('similarity_matrix', engine, if_exists='replace', index=True)
print("유사도 데이터가 'similarity_matrix' 테이블로 DB에 적재되었습니다.")
