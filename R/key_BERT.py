'''
review text 에 대한 BERT 모델로 keyword를 추출하는 모듈입니다. 
사용하지 않습니다. 

'''



from keybert import KeyBERT

# Initialize KeyBERT with default BERT model
kw_model = KeyBERT()

# Your review text
review = "The games controls are way too hard to learn so I can't even play cause I can't figure out the basic controls of the game so I don't recommend this game"

# Extract keywords with BERT embeddings
keywords = kw_model.extract_keywords(
    review,
    keyphrase_ngram_range=(1, 2),           # Include single words and bigrams
    top_n=5,                                # Return top 5 keywords
    stop_words='english, game, review'      # Remove English stopwords
)

# Display results
print("Top keywords with scores:")
for keyword, score in keywords:
    print(f"- {keyword}: {score:.3f}")
