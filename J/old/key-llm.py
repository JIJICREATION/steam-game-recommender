import mysql.connector
import openai

# OpenAI API 키 설정
openai.api_key = 'your-api-key'  # 여기에 실제 OpenAI API 키를 입력하세요.

# MariaDB 연결
def connect_to_mariadb():
    return mysql.connector.connect(
        host='your-mariadb-host',  # MariaDB 호스트
        user='your-mariadb-user',  # 사용자
        password='your-mariadb-password',  # 비밀번호
        database='your-database-name'  # 데이터베이스 이름
    )

# MariaDB에서 상위 20% 내림차순으로 데이터 70개 가져오기
def fetch_top_20_percent_data():
    conn = connect_to_mariadb()
    cursor = conn.cursor()

    # MariaDB에서 상위 20% 데이터를 내림차순으로 가져오기
    cursor.execute("""
        SELECT id, text
        FROM texts
        ORDER BY some_column DESC  -- 이 컬럼에 대해 내림차순으로 정렬
        LIMIT (SELECT FLOOR(COUNT(*) * 0.2) FROM texts);
    """)
    
    rows = cursor.fetchall()  # 가져온 데이터
    conn.close()

    return rows[:70]  # 상위 70개만 반환 (20%에서 상위 70개)

# LLM(예: OpenAI GPT 모델)으로 텍스트 처리
def process_with_llm(text):
    response = openai.Completion.create(
        model="text-davinci-003",  # 예시로 text-davinci-003 모델 사용
        prompt=text,
        max_tokens=150  # 필요한 만큼의 토큰 설정
    )
    return response.choices[0].text.strip()

# DB에서 데이터를 가져오고, LLM으로 처리하여 결과 출력
def process_and_display_results():
    # DB에서 데이터 가져오기
    rows = fetch_top_20_percent_data()

    # 처리된 결과를 저장할 리스트
    results = []

    for row in rows:
        id, text = row
        print(f"Processing text ID {id}...")

        # LLM으로 텍스트 처리
        processed_text = process_with_llm(text)
        
        # 결과 저장
        results.append((id, processed_text))
    
    # 결과 출력
    for result in results:
        print(f"ID: {result[0]}, Processed Text: {result[1]}")

# 실행
process_and_display_results()
