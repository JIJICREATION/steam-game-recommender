<<<<<<< HEAD
#db_utils.py (DB에서 app_id 조회, json으로 적재)
=======
#db_utils.py (DB에서 app_id 조회, 컬럼추가, json으로 적재)
>>>>>>> bb5fe532052a65568f5396c5279c58effc69f8cc

import os
import pymysql
from dotenv import load_dotenv

def get_connection():
    load_dotenv()
    dbuser = os.getenv('dbuser')
    password = os.getenv('password')
    host = os.getenv('host')
    port = int(os.getenv('port', 3306))
    dbname = os.getenv('name')

    conn = pymysql.connect(
        host=host,
        user=dbuser,
        password=password,
        db=dbname,
        port=port,
        charset="utf8mb4"
    )
    return conn

<<<<<<< HEAD
=======
def ensure_user_tags_column():
    """
    LIST_OF_MOBA_INDI 테이블에 user_tags 컬럼이 없으면 추가.
    이미 있으면 무시.
    MySQL 8.0+에서는 'ADD COLUMN IF NOT EXISTS' 문법이 가능.
    (MariaDB / MySQL 5.x 이하에서는 처리 다를 수 있음)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # MySQL 8.0+: 
            #    ALTER TABLE table_name ADD COLUMN IF NOT EXISTS ...
            # 만약 버전이 낮으면, 아래 구문 지원 안 될 수 있음.
            sql = """
            ALTER TABLE LIST_OF_MOBA_INDI
                ADD COLUMN IF NOT EXISTS user_tags TEXT NULL
            """
            cur.execute(sql)
        conn.commit()
    except pymysql.err.OperationalError as e:
        # 어떤 MySQL/MariaDB 버전에서는 IF NOT EXISTS가 지원 안 되어 에러가 날 수 있음
        # 1060 : duplicate column name
        if e.args[0] == 1060:
            print("[INFO] 'user_tags' 컬럼이 이미 존재하여 스킵")
        else:
            raise e
    finally:
        conn.close()

>>>>>>> bb5fe532052a65568f5396c5279c58effc69f8cc
def fetch_app_ids():
    """
    DB에서 app_id 목록 SELECT
    """
    conn = get_connection()
    app_ids = []
    try:
        with conn.cursor() as cur:
            sql = "SELECT app_id FROM LIST_OF_MOBA_INDI"
            cur.execute(sql)
            rows = cur.fetchall()  # e.g. [(572220,), (123456,)]
            for row in rows:
                app_ids.append(row[0])
    finally:
        conn.close()

    return app_ids

def update_app_tags(app_id, tags_json):
    """
    user_tags 칼럼에 태그 JSON을 저장
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
            UPDATE LIST_OF_MOBA_INDI
               SET user_tags = %s
             WHERE app_id = %s
            """
            cur.execute(sql, (tags_json, app_id))
        conn.commit()
    finally:
        conn.close()

<<<<<<< HEAD
=======



>>>>>>> bb5fe532052a65568f5396c5279c58effc69f8cc
