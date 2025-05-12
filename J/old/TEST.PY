import pandas as pd
import ast
import numpy as np
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.types import UnicodeText, Float
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics.pairwise import cosine_similarity

# 1. 로깅 최소화
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)

# 2. DB 접속 정보 (하드 코딩; 필요시 환경 변수로 대체)
db_host = "bootcampproject2t1steam.cdi60g8ggh0i.ap-southeast-2.rds.amazonaws.com"
db_port = 3306
db_user = "minsung"
db_password = "password"
db_name = "steam_lit_project"
connection_string = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
engine = create_engine(connection_string, pool_pre_ping=True)

# 3. TITLELIST 테이블에서 게임 매핑 정보 불러오기 (컬럼: app_id, name)
try:
    title_df = pd.read_sql("SELECT app_id, name FROM TITLELIST", engine)
    title_df['app_id'] = title_df['app_id'].astype(str).str.strip()
    print("TITLELIST 데이터 예시:")
    print(title_df.head())
except SQLAlchemyError as e:
    print("TITLELIST 데이터 불러오는 중 오류 발생:", str(e))
    title_df = pd.DataFrame(columns=['app_id', 'name'])

# 4. SIMILAR_GAMES 테이블에서 추천 게임 정보 불러오기
def fetch_similar_games(engine):
    query = text("""
        SELECT game_app_id, recommended_app_id, recommended_title, user_tags
        FROM SIMILAR_GAMES
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df

df_similar = fetch_similar_games(engine)
df_similar['game_app_id'] = df_similar['game_app_id'].astype(str).str.strip()
print("SIMILAR_GAMES 데이터 예시:")
print(df_similar.head())

# 5. user_tags 파싱 (문자열이면 ast.literal_eval로 리스트로 변환)
def parse_tags(tag_field):
    if isinstance(tag_field, str):
        try:
            return ast.literal_eval(tag_field)
        except Exception:
            return []
    elif isinstance(tag_field, list):
        return tag_field
    else:
        return []

df_similar['user_tags'] = df_similar['user_tags'].apply(parse_tags)

# 6. 각 원본 게임(app_id)별로 상위 9개 추천 게임만 선택하고,
#    각 추천 게임의 태그 기반 유사도 계산 후 결과를 하나의 행으로 피벗
records = []
grouped = df_similar.groupby('game_app_id')
for app_id, group in grouped:
    # 상위 9개 추천 게임만 선택 (추천 앱 아이디 기준 오름차순 정렬)
    group = group.sort_values('recommended_app_id').head(9).copy()
    if len(group) < 9:
        # 만약 해당 원본 게임의 추천 게임 수가 9개 미만이면, 나머지는 NaN으로 채워줌
        group = group.reindex(range(9))
    # 추천 게임의 제목과 태그 리스트
    rec_titles = group['recommended_title'].tolist()
    rec_tags = group['user_tags'].tolist()
    
    # MultiLabelBinarizer로 태그 벡터화
    mlb = MultiLabelBinarizer()
    try:
        tag_matrix = mlb.fit_transform(rec_tags)
    except Exception as e:
        print(f"app_id {app_id} 태그 벡터화 오류:", e)
        continue
        
    # 코사인 유사도 행렬 계산 (9 x 9)
    sim_matrix = cosine_similarity(tag_matrix)
    
    # 각 추천 게임별로 자기 자신을 제외한 나머지와의 평균 유사도 계산
    individual_sim = []
    for i in range(len(rec_titles)):
        # 만약 rec_tags[i]가 NaN 등으로 인해 결측이면 NaN 처리
        if rec_tags[i] is None:
            individual_sim.append(np.nan)
        else:
            # 자기 자신 열 제외
            row = np.delete(sim_matrix[i], i)
            individual_sim.append(np.mean(row))
    
    # 피벗할 딕셔너리 생성: 한 행에 각 추천 게임별 정보 삽입
    record = {'game_app_id': app_id}
    for idx in range(9):
        rec_id_key = f"recommended_app_id_{idx+1}"
        rec_title_key = f"recommended_title_{idx+1}"
        sim_key = f"similarity_{idx+1}"
        # 각 추천 게임 정보가 존재하면 값 사용, 없으면 NaN
        record[rec_id_key] = group['recommended_app_id'].iloc[idx] if idx < len(group) else None
        record[rec_title_key] = rec_titles[idx] if idx < len(rec_titles) else None
        record[sim_key] = individual_sim[idx] if idx < len(individual_sim) else None
    records.append(record)

if records:
    final_df = pd.DataFrame(records)
else:
    final_df = pd.DataFrame()

print("유사도 계산 결과 DataFrame 크기 (각 원본 게임당 1행, 총 2078행 예상):", final_df.shape)
print(final_df.head())

# 7. TITLELIST와 병합하여 원본 게임 이름("name") 추가 (game_app_id 기준)
final_df['game_app_id'] = final_df['game_app_id'].astype(str).str.strip()
merged_df = final_df.merge(title_df, left_on='game_app_id', right_on='app_id', how='left')
merged_df = merged_df.drop(columns=['app_id'])
# 원하는 열 순서로 재정렬: 게임 이름(name), game_app_id, 그리고 9개의 추천 정보 컬럼들
cols_order = ['name', 'game_app_id']
for i in range(1, 10):
    cols_order.extend([f"recommended_app_id_{i}", f"recommended_title_{i}", f"similarity_{i}"])
merged_df = merged_df[cols_order]

print("최종 결과 DataFrame (게임 이름 포함) 크기:", merged_df.shape)
print(merged_df.head())

# 8. 최종 결과를 DB의 MATRIX 테이블에 적재 (문자열 컬럼은 UnicodeText, 실수는 Float)
dtype_dict = {
    'name': UnicodeText(collation='utf8mb4_unicode_ci'),
    'game_app_id': UnicodeText(collation='utf8mb4_unicode_ci')
}
for i in range(1, 10):
    dtype_dict[f"recommended_app_id_{i}"] = UnicodeText(collation='utf8mb4_unicode_ci')
    dtype_dict[f"recommended_title_{i}"] = UnicodeText(collation='utf8mb4_unicode_ci')
    dtype_dict[f"similarity_{i}"] = Float()

try:
    merged_df.to_sql('MATRIX', engine, if_exists='replace', index=False, dtype=dtype_dict)
    print("최종 유사도 결과(각 원본 게임당 9개 추천 정보)가 'MATRIX' 테이블에 성공적으로 적재되었습니다.")
except SQLAlchemyError as e:
    print("데이터 적재 중 오류 발생:", str(e))
