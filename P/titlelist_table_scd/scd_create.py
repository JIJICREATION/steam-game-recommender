import os
import pymysql
from dotenv import load_dotenv

def get_connection():
    load_dotenv()
    dbuser = os.getenv("dbuser")
    password = os.getenv("password")
    host = os.getenv("host")
    port = int(os.getenv("port", 3306))
    dbname = os.getenv("name")
    conn = pymysql.connect(
        host=host,
        user=dbuser,
        password=password,
        db=dbname,
        port=port,
        charset="utf8mb4"
    )
    return conn

def create_scd_table():
    """
    TITLELIST 테이블을 SCD(유효 기간) 구조로 생성 (없으면)
    - PK: (app_id, start_date)
    - user_tags 컬럼은 TEXT 형식으로 정의 (태그 ID 리스트를 JSON 문자열로 저장)
    - 모든 레코드에 대해 end_date는 날짜 형식으로 관리되며, 활성 레코드는 '9999-12-31'로 표시
    """
    create_sql = """
    CREATE TABLE IF NOT EXISTS TITLELIST (
      app_id      BIGINT      NOT NULL,
      name        VARCHAR(255),
      user_tags   TEXT,
      price_us    FLOAT,
      releaseYear VARCHAR(10),
      userScore   FLOAT,
      start_date  DATETIME    NOT NULL,
      end_date    DATETIME    NOT NULL DEFAULT '9999-12-31',
      PRIMARY KEY (app_id, start_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(create_sql)
            conn.commit()
        print("[DB] SCD 테이블 'TITLELIST' 가 준비되었습니다.")
    finally:
        conn.close()

if __name__ == "__main__":
    create_scd_table()
