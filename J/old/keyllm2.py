

"""
이 코드는 로컬에 저장된 CSV 파일(예: processed_reviews.csv)에서 리뷰 텍스트를 불러와,
OpenAI API를 사용하여 KEYLLM으로 각 리뷰의 키워드를 추출하고, 그 결과를 원본 리뷰 텍스트 옆에 추가하여
새로운 CSV 파일(reviews_keyllm.csv)로 저장하는 코드입니다.

[기본 모델 및 설정]
- 기본 모델: 별도로 모델명을 지정하지 않았습니다.
  보통 text-davinci-003 모델을 사용.
- 토큰(max_tokens): 명시적으로 설정하지 않은 경우, 해당 모델의 기본 최대 토큰 수 4097토큰
- 템피러처(temperature): 별도로 설정하지 않으면 기본값(대부분 1.0)이 사용됩니다.

"""


import pandas as pd
import openai
from keybert import KeyLLM
from keybert.llm import OpenAI as OpenAI_KLLM

# OpenAI의 Completions 기능을 monkey-patch하여 KEYLLM과 호환되도록 함
openai.completions = openai.Completion

# 하드코딩된 OpenAI API 키 및 파일 경로 (본인의 값으로 변경하세요)
OPENAI_API_KEY = "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"
INPUT_CSV_PATH = r"C:\Users\abwm2\Desktop\BootCamp\TIL\팀프로젝트 steam\J\processed_reviews.csv"
OUTPUT_CSV_PATH = r"C:\Users\abwm2\Desktop\BootCamp\TIL\팀프로젝트 steam\J\reviews1_with_keyllm.csv"

# CSV 파일에서 리뷰 텍스트 읽기 및 전처리
df = pd.read_csv(INPUT_CSV_PATH)
df = df[df["review_text"].notna()]                # NaN 제거
df = df[df["review_text"].str.strip() != ""]       # 빈 문자열 제거
df["review_text"] = df["review_text"].astype(str)   # 모든 리뷰 텍스트를 문자열로 변환

# 리뷰 데이터 중 상위 100건만 선택 (테스트용)
df = df.head(100)
reviews = df["review_text"].tolist()
print(f"총 {len(reviews)}개의 리뷰 데이터를 불러왔습니다.")

# OpenAI API 및 KEYLLM 초기화
openai.api_key = OPENAI_API_KEY
llm_client = OpenAI_KLLM(openai)
llm_client.generator_kwargs = {"temperature": 0.3}
kw_model = KeyLLM(llm_client)

# 각 리뷰에 대해 KEYLLM으로 키워드 추출 (예: [['Quill cos', ...], ...])
keyllm_results = kw_model.extract_keywords(reviews)

# review_text 컬럼 바로 옆에 keyllm_result 컬럼 삽입
df.insert(loc=df.columns.get_loc("review_text") + 1, column="keyllm_result", value=keyllm_results)

# 결과 CSV 파일로 저장 (UTF-8 인코딩)
df.to_csv(OUTPUT_CSV_PATH, index=False, encoding="utf-8")
print(f"결과 CSV 파일이 생성되었습니다: {OUTPUT_CSV_PATH}")
