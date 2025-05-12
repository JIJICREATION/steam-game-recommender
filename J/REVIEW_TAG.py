


"""
[코드 전체 요약]
- OpenAI API를 사용해 게임 리뷰에서 8가지 측면(Game, Story, Graphics, Sound, Content, Originality, Stability, Convenience)에 대한 감성 점수(-1,0,1)를 분석하는 코드
- MariaDB에서 모든 리뷰 데이터를 가져와 OpenAI GPT 모델로 분석 수행 후 결과를 저장하는 프로세스 구현
- 분석된 감성 점수는 DB 내 REVIEW_TAG 테이블에 저장되어 관리됨

"""







import mysql.connector
import openai
import json
import pandas as pd
from google.colab import files

# OpenAI API 키 설정 (본인의 API 키로 변경)
openai.api_key = "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"

# MariaDB 연결 정보 (하드코딩)
db_host = "bootcampproject2t1steam.cdi60g8ggh0i.ap-southeast-2.rds.amazonaws.com"
db_port = 3306
db_user = "minsung"
db_password = "password"
db_name = "steam_lit_project"

def create_prompt(review_text: str) -> str:
    """
    리뷰 텍스트를 바탕으로 8개 측면에 대해 -1, 0, 1 점수를 매기도록 하는 프롬프트를 생성합니다.
    """
    return f"""
You are an expert in game review sentiment analysis.

Please read the following game review carefully and evaluate its sentiment in each of the eight aspects listed below. Use the following guidelines:

1. "Game": Evaluate the core gameplay, system mechanics, and overall fun.
2. "Story": Evaluate the scenario, narrative, and dialogues.
3. "Graphics": Evaluate the visual style, such as 2.5D, cutscenes, and visual effects.
4. "Sound": Evaluate the quality of music, OST, and sound effects.
5. "Content": Evaluate the volume of content, side quests, and variety of game modes.
6. "Originality": Evaluate innovation, new ideas, and unique mechanics.
7. "Stability": Evaluate bugs, performance issues, and crashes.
8. "Convenience": Evaluate controls, UI/UX, and overall accessibility. (If the review specifically criticizes controls, aim, keyboard/mouse input, or UI, assign -1 to Convenience.)

Scoring rules:
- If the review explicitly praises the aspect, assign +1.
- If the review explicitly criticizes the aspect, assign -1.
- If the aspect is not clearly mentioned or is neutral, assign 0.

IMPORTANT: Return ONLY a valid JSON object with exactly the following 8 keys (in this order):
"Game", "Story", "Graphics", "Sound", "Content", "Originality", "Stability", "Convenience".
Each key must map to an integer value (-1, 0, or 1). Do not include any additional text or explanations.

Review:
\"\"\"{review_text}\"\"\"
"""

def analyze_review(review_text: str) -> dict:
    """
    주어진 리뷰 텍스트에 대해 OpenAI LLM을 호출하여, 8개 측면별 감성 점수를 도출합니다.
    """
    prompt = create_prompt(review_text)
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # 필요하면 GPT-4로 변경 가능
            messages=[
                {"role": "system", "content": "You are an expert game review sentiment analysis assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=1,
            max_tokens=4096
        )
        content = response["choices"][0]["message"]["content"].strip()
        return json.loads(content)
    except Exception as e:
        print("Error during OpenAI API call or JSON parsing:", e)
        return {
            "Game": 0,
            "Story": 0,
            "Graphics": 0,
            "Sound": 0,
            "Content": 0,
            "Originality": 0,
            "Stability": 0,
            "Convenience": 0
        }

# DB 연결 및 리뷰 데이터 불러오기
try:
    conn = mysql.connector.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database=db_name
    )
    cursor = conn.cursor()
    
    # REVIEW_TAG 테이블을 생성 (대소문자 일관성 유지)
    create_table_query = """
    DROP TABLE IF EXISTS REVIEW_TAG;
    CREATE TABLE REVIEW_TAG (
      id INT AUTO_INCREMENT PRIMARY KEY,
      review_id INT NOT NULL,
      game INT NOT NULL,
      story INT NOT NULL,
      graphics INT NOT NULL,
      sound INT NOT NULL,
      content INT NOT NULL,
      originality INT NOT NULL,
      stability INT NOT NULL,
      convenience INT NOT NULL
    );
    """
    for query in create_table_query.split(";"):
        if query.strip():
            cursor.execute(query)
    conn.commit()
    
    # GAME_REVIEW 테이블에서 모든 리뷰 (review_id, review_text) 불러오기
    select_query = "SELECT review_id, review_text FROM GAME_REVIEW"
    cursor.execute(select_query)
    rows = cursor.fetchall()
    
    print(f"총 {len(rows)}개의 리뷰를 가져왔습니다.")
    
    # 각 리뷰 분석 후 REVIEW_TAG 테이블에 저장
    insert_query = """
    INSERT INTO REVIEW_TAG (
      review_id, game, story, graphics, sound, content, originality, stability, convenience
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    for idx, (review_id, review_text) in enumerate(rows):
        print(f"\n=== {idx+1}/{len(rows)}번 리뷰 분석 (review_id={review_id}) ===")
        print(f"리뷰 텍스트:\n{review_text}\n")
        
        analysis = analyze_review(review_text)
        
        cursor.execute(insert_query, (
            review_id,
            analysis["Game"],
            analysis["Story"],
            analysis["Graphics"],
            analysis["Sound"],
            analysis["Content"],
            analysis["Originality"],
            analysis["Stability"],
            analysis["Convenience"]
        ))
        conn.commit()
    
    cursor.close()
    conn.close()

except Exception as e:
    print("DB 연결 또는 쿼리 오류:", e)