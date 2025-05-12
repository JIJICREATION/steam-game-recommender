<<<<<<< HEAD
'''
유사단어의 범위를 문서 전체로 확장하기 위한 모듈입니다. 
현재 연구중인 코드 입니다. 
'''


import pandas as pd
from ast import literal_eval

# CSV 파일 로드
df = pd.read_csv('D:/T1/reviews_with_improved_keywords_v2.csv')

# top_keywords 열의 문자열을 리스트로 변환
df['top_keywords'] = df['top_keywords'].apply(literal_eval)

# 모든 키워드를 하나의 리스트로 합치기
all_keywords = [keyword for keywords in df['top_keywords'] for keyword in keywords]

# 중복 제거 및 정렬
unique_keywords = sorted(set(all_keywords))

# 결과 출력
print("단어집:")
for keyword in unique_keywords:
    print(keyword)

# 단어 수 출력
print(f"\n총 단어 수: {len(unique_keywords)}")
=======
import pandas as pd
from textblob import Word
from nltk.corpus import wordnet
from collections import defaultdict
import difflib

# 1. 데이터 로드 및 전처리
df = pd.read_csv('D:/T1/reviews_with_improved_keywords_v3.csv')
all_keywords = set()

for entry in df['top_keywords']:
    if pd.notna(entry):
        keywords = eval(entry)
        all_keywords.update(keywords)

unique_keywords = list(all_keywords)

# 2. 의미 기반 단어 그룹 생성 함수
def generate_word_groups(keywords):
    word_groups = defaultdict(list)
    processed = set()
    
    # 동의어 및 어간 추출
    for kw in keywords:
        if kw in processed:
            continue
            
        # TextBlob을 이용한 표제어 추출
        base_form = Word(kw).lemmatize()
        
        # WordNet을 이용한 동의어 확장
        synonyms = set()
        for syn in wordnet.synsets(kw):
            for lemma in syn.lemmas():
                synonyms.add(lemma.name().replace('_', ' '))
        
        # 문자열 유사도 검출
        string_matches = difflib.get_close_matches(kw, keywords, n=5, cutoff=0.7)
        
        # 그룹 통합
        combined_group = {kw, base_form} | synonyms | set(string_matches)
        filtered_group = [w for w in combined_group if w in keywords]
        
        # 대표 단어 선택 (가장 짧고 일반적인 단어)
        main_term = min(filtered_group, key=lambda x: (len(x), x))
        
        for word in filtered_group:
            if word not in processed:
                word_groups[main_term].append(word)
                processed.add(word)

    return word_groups

# 3. 통합 사전 생성
word_groups = generate_word_groups(unique_keywords)
unification_dict = {}

for main_term, group in word_groups.items():
    for word in group:
        unification_dict[word] = main_term

# 4. 결과 출력
print("생성된 단어 그룹 (일부):")
for main, group in list(word_groups.items())[:10]:
    print(f"• {main}: {group[:5]}...")

print("\n통합 사전 예시:")
for k, v in list(unification_dict.items())[:15]:
    print(f"{k:>20} → {v}")
>>>>>>> bb5fe532052a65568f5396c5279c58effc69f8cc
