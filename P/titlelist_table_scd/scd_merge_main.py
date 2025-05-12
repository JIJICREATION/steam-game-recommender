import os
import pymysql
from dotenv import load_dotenv
from scd_create import create_scd_table
from scd_upsert import upsert_scd_version

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

def merge_moba_indi_current():
    """
    1) LIST_OF_MOBA_INDI 테이블에서 현재 최신 데이터(각 app_id 1행) 읽기
    2) TITLELIST 테이블에 upsert_scd_version() 호출
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
            SELECT app_id, name, price_us, releaseYear, userScore, user_tags
            FROM LIST_OF_MOBA_INDI
            """
            cur.execute(sql)
            rows = cur.fetchall()
            print(f"[INFO] current LIST_OF_MOBA_INDI rows = {len(rows)}")

        for i, row in enumerate(rows, start=1):
            app_id, name, price_us, releaseYear, userScore, user_tags = row
            upsert_scd_version(
                app_id,
                name=name,
                price_us=price_us,
                releaseYear=releaseYear,
                userScore=userScore,
                user_tags=user_tags
            )
            print(f"[{i}/{len(rows)}] current merged app_id={app_id}")
    finally:
        conn.close()

def merge_LIST_OF_MOBA_INDI_HISTORY():
    """
    1) LIST_OF_MOBA_INDI_HISTORY 테이블(과거 이력)에서
       (app_id, name, price_us, releaseYear, userScore, changed_at)를 불러와
    2) upsert_scd_version() 호출 시, changed_at을 start_date 값으로 사용
       -> TITLELIST에 과거 버전이 start_date=changed_at, end_date=... 형태로 저장됨
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
            SELECT app_id,
                   name,
                   price_us,
                   releaseYear,
                   userScore,
                   changed_at
            FROM LIST_OF_MOBA_INDI_HISTORY
            ORDER BY changed_at
            """
            cur.execute(sql)
            rows = cur.fetchall()
            print(f"[INFO] history rows = {len(rows)}")

        for i, row in enumerate(rows, start=1):
            app_id    = row[0]
            name      = row[1]
            price_us  = row[2]
            releaseYr = row[3]
            score     = row[4]
            changed_t = row[5]  # 예: '2025-03-20 15:23:00'

            upsert_scd_version(
                app_id,
                name=name,
                price_us=price_us,
                releaseYear=releaseYr,
                userScore=score,
                start_date=str(changed_t)  # changed_at을 start_date으로 사용
            )
            print(f"[{i}/{len(rows)}] history merged app_id={app_id}")

    finally:
        conn.close()

def main():
    # A) TITLELIST 테이블 SCD 구조 보장
    create_scd_table()

    # B) 현재 LIST_OF_MOBA_INDI 데이터를 TITLELIST로 업서트
    merge_moba_indi_current()

    # C) 과거 LIST_OF_MOBA_INDI_HISTORY 데이터를 TITLELIST로 업서트
    merge_LIST_OF_MOBA_INDI_HISTORY()

    print("[DONE] All merges completed. Check TITLELIST for SCD versions.")

if __name__ == "__main__":
    main()
