## E-commerce 기반 스팀 게임 추천 시스템

## 프로젝트 개요
Steam 게임 데이터를 수집하고, 유사 게임을 추천하는 시스템을 구축했습니다.
리뷰 기반 텍스트 분석과 게임 메타데이터를 결합하여, 유저 맞춤형 추천 기능을 제공합니다.

---

## 주요 기능
1. **데이터 수집 (크롤링 + API)**
   - **Algolia(steamdb) + Selenium**: 스팀 게임 리스트 및 +버튼 태그 정보 크롤링
   - **중복 태그 크롤 방지**: 캐시 사용으로 크롤링 속도 향상
   - **유사 게임**(More Like This) 크롤링: `SIMILAR_GAMES` 테이블에 저장

2. **데이터베이스 (MySQL/MariaDB)**
   - **TITLELIST**: SCD(슬로우 체인지 디멘션) 방식으로 게임 정보 이력 관리
   - **SIMILAR_GAMES**: 게임별 추천 게임 목록과 태그
   - **TAGS**: 태그 문자열 ↔ 정수 ID 매핑
   - **GAME_REVIEW** & **REVIEW_TAG**: 리뷰 원문 및 감성 분석 결과 저장

3. **OpenAI GPT 감성 분석**
   - 리뷰 텍스트 입력 → GPT 모델로 8개 측면(Game, Story, Graphics 등)에 대한 -1/0/1 점수 추출
   - 분석 결과를 `REVIEW_TAG` 테이블에 JSON 형태로 저장

4. **Streamlit 대시보드**
   - **태그 필터링**: 여러 태그를 선택해 해당 태그들이 포함된 게임만 조회
   - **키워드 분석**: 긍정/부정 키워드 빈도, 워드클라우드, 바 차트, 버블 차트
   - **추천 게임**: `SIMILAR_GAMES` 조회
   - **리뷰 상세**: 긍정/부정 리뷰 텍스트 확인

---

## 기술 스택
- **언어**: Python 3
- **크롤링**: requests, Selenium, webdriver_manager
- **DB**: MySQL/MariaDB (PyMySQL, mysql.connector)
- **AI 분석**: OpenAI API (GPT-3.5)
- **웹 대시보드**: Streamlit, Plotly, WordCloud, streamlit-elements
- **기타**: dotenv, pandas, json, collections, time/os 등

---

## 설치 & 실행

1. **환경 설정**
   - Python 3.8+ 권장
   - `pip install -r requirements.txt`
   - `.env` 파일에서 DB 접속 정보 및 OpenAI API Key 설정
     ```bash
     DB_HOST=your-db-host
     DB_USER=your-db-user
     DB_PASSWORD=your-db-password
     DB_NAME=steam_lit_project
     DB_PORT=3306
     OPENAI_API_KEY=sk-xxxx...
     ```
   - 크롬 브라우저 설치

2. **DB 초기화**
   - 테이블: `TITLELIST`, `SIMILAR_GAMES`, `TAGS`, `GAME_REVIEW`, `REVIEW_TAG`
   - 필요 시 `create_table_query` 또는 SQL 수동 실행

3. **데이터 수집**
   - `python update_titlelist.py`  
     - Algolia(steamdb) API & Steam +버튼 태그 크롤링  
     - SCD 업서트하여 `TITLELIST` 저장
   - `python update_similargames.py`  
     - `game_app_id` 별 More Like This 페이지 크롤, `SIMILAR_GAMES` 저장

4. **리뷰 감성 분석**
   - `python analyze_reviews.py`  
     - `GAME_REVIEW`에서 리뷰 읽음 → OpenAI GPT 감성 분석 → `REVIEW_TAG`에 -1/0/1 저장

5. **Streamlit 대시보드**
   - `streamlit run streamlit_app.py`
   - 웹 브라우저(보통 `http://localhost:8501`) 접속하여 태그/키워드 필터링 및 리뷰 분석 결과 확인

---

## 디렉토리 구조 (예시)   
├── update_titlelist.py   
├── update_similargames.py   
├── analyze_reviews.py   
├── streamlit_app.py   
├── requirements.txt   
├── .env     
├── .gitignore     
└── README.md       


---

## 데모 / 스크린샷

- **크롤링 예시**  
  (원하는 스크린샷 이미지 삽입)

- **대시보드 화면**  
  (Streamlit UI, Bar/Bubble 차트/워드클라우드 등 시각화 예시 삽입)

---

## 참고
- **OpenAI 문서**: [OpenAI API Reference](https://platform.openai.com/docs/introduction)
- **Streamlit**: [Streamlit Docs](https://docs.streamlit.io)

---

## 라이선스
- MIT License (예시)  
- 데이터 수집 시, Steam 이용 약관 및 개인정보 보호 정책을 준수하세요.

---
## 담당한 기능 (by @jiminseong)

프로젝트 내에서 저는 J/ 폴더에 포함된 리뷰 수집, 감성 분석, 유사 게임 크롤링, 유사도 계산 등 핵심 데이터 파이프라인을 담당했습니다.

리뷰 수집 & 전처리

MariaDB에 저장된 게임 app_id를 기준으로 Steam 리뷰 API를 호출해 리뷰 데이터를 수집했습니다.

수집된 리뷰 텍스트는 이모지/HTML 태그/BBCode 등을 제거해 깔끔하게 전처리한 뒤, GAME_REVIEW 테이블에 적재했습니다.

GPT 기반 감성 분석

OpenAI GPT-3.5 API를 활용하여 리뷰 텍스트에 대해 8가지 측면(Game, Story, Graphics, etc.)별 감성 점수(-1/0/1)를 추출했습니다.

분석 결과는 REVIEW_TAG 테이블에 정형화된 형태로 저장했습니다.

유사 게임 수집 (Selenium 크롤링)

Steam 웹사이트의 "More Like This" 추천 페이지를 Selenium으로 크롤링하여, 각 게임별로 추천된 게임 목록과 제목을 수집했습니다.

수집된 데이터는 SIMILAR_GAMES 테이블에 저장했습니다.

유사도 기반 추천

게임 태그 데이터를 이진 벡터화하고, cosine_similarity로 유사도를 계산한 후 similarity_matrix 테이블로 저장했습니다.

이 과정은 추후 유사 게임 추천 기능의 핵심 기반이 되며, Streamlit 대시보드에서 활용됩니다
