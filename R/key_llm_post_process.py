'''
csv에서 df를 뽑고
df의 특정 열에 대해서 

1. 중요순 재정렬
<<<<<<< HEAD
2. 동의서 처리
3. 불용어 처리
4. top3 로 단어 추리기
=======
2. 동의어 처리
3. 불용어 처리
4. top10 로 단어 추리기
>>>>>>> bb5fe532052a65568f5396c5279c58effc69f8cc

를 시행합니다. 

csv 부분은 db로 대체되어야 합니다. 




'''


import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.metrics.pairwise import cosine_similarity
from nltk.stem import WordNetLemmatizer
import nltk

# CSV 파일 로드
df = pd.read_csv('D:/T1/reviews_with_keyllm_keywords.csv')

lemmatizer = WordNetLemmatizer()
custom_stop_words = ENGLISH_STOP_WORDS.union(['game', 'play', 'term', 'slang', 'expression', 'gaming', 'tty', 'sh tty','sh'])

# 동의어 사전 정의 (필요에 따라 확장 가능)
synonyms = {
    'graphics': ['visuals']
}

def process_keywords(keywords):
    keywords = eval(keywords)
    return [word.lower() for sublist in keywords for word in sublist]

df['processed_keywords'] = df['keyLLM_keywords'].apply(process_keywords)

# 1. TF-IDF를 통한 중요 키워드 순으로 키워드 재정렬
def rearrange_keywords_tfidf(keywords):
    if not keywords:
        return []
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([' '.join(keywords)])
    feature_names = vectorizer.get_feature_names_out()
    tfidf_scores = tfidf_matrix.toarray()[0]
    return [feature_names[i] for i in tfidf_scores.argsort()[::-1]]

df['rearranged_keywords'] = df['processed_keywords'].apply(rearrange_keywords_tfidf)

# 2. 유사단어 통일 (동의어 사전 활용)
def unify_similar_words(keywords):
    unified = []
    for word in keywords:
        replaced = False
        for key, values in synonyms.items():
            if word in values:
                unified.append(key)
                replaced = True
                break
        if not replaced:
            unified.append(word)
    return list(dict.fromkeys(unified))  # 중복 제거

df['unified_keywords'] = df['rearranged_keywords'].apply(unify_similar_words)

# 3. 불용어 처리
def remove_stop_words(keywords):
    return [word for word in keywords if word not in custom_stop_words]

df['filtered_keywords'] = df['unified_keywords'].apply(remove_stop_words)

# 4. Top3로 추리기
<<<<<<< HEAD
df['top_keywords'] = df['filtered_keywords'].apply(lambda x: x[:3])

# 결과 저장 및 출력
df.to_csv('D:/T1/reviews_with_improved_keywords_v2.csv', index=False)
=======
df['top_keywords'] = df['filtered_keywords'].apply(lambda x: x[:9])

# 결과 저장 및 출력
df.to_csv('D:/T1/reviews_with_improved_keywords_v3.csv', index=False)
>>>>>>> bb5fe532052a65568f5396c5279c58effc69f8cc
print(df[['review_text', 'top_keywords']].head())
