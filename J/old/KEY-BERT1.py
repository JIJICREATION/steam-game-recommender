import pandas as pd
from keybert import KeyBERT
from multiprocessing import Pool

# 1. CSV 파일 읽기
df = pd.read_csv(r'C:\Users\abwm2\Desktop\BootCamp\TIL\팀프로젝트 steam\J\processed_reviews.csv')  # 파일 경로에 맞게 변경

# 2. KeyBERT 모델 로드
kw_model = KeyBERT()

# 3. 키워드 추출 함수
def extract_keywords(text):
    if isinstance(text, str) and text.strip():  # 텍스트가 문자열이고 비어있지 않은지 확인
        keywords = kw_model.extract_keywords(text, top_n=5)  # 상위 5개의 키워드 추출
        # 키워드와 그에 해당하는 스코어를 튜플로 반환
        return [(keyword[0], keyword[1]) for keyword in keywords]  # (키워드, 스코어) 튜플 반환
    else:
        return []  # 텍스트가 없거나 유효하지 않으면 빈 리스트 반환

# 병렬 처리를 위한 helper 함수
def apply_parallel(df, func):
    with Pool() as pool:
        result = pool.map(func, df)
        pool.close()  # 프로세스 종료
        pool.join()  # 모든 프로세스가 종료될 때까지 기다림
    return result

# 4. 각 리뷰에 대해 키워드 추출 (병렬 처리)
df['keywords'] = apply_parallel(df['review_text'], extract_keywords)

# 5. 결과 출력: 첫 몇 개의 결과 출력
print(df[['app_id', 'review_text', 'keywords']].head())  # 데이터 프레임 상위 5개 행 출력

# 6. 결과를 새 CSV 파일로 저장
df.to_csv('review_keyword.csv', index=False)



