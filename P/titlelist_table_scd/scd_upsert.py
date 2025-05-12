import os
import pymysql
import ast
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

def get_connection():
    load_dotenv()
    dbuser = os.getenv("dbuser")
    password = os.getenv("password")
    host = os.getenv("host")
    port = int(os.getenv("port", 3306))
    dbname = os.getenv("name")
    return pymysql.connect(
        host=host,
        user=dbuser,
        password=password,
        db=dbname,
        port=port,
        charset="utf8mb4"
    )

def load_tag_mapping(mapping_file="tag_mapping.json"):
    if os.path.exists(mapping_file):
        with open(mapping_file, "r", encoding="utf-8") as f:
            mapping = json.load(f)
        return mapping
    else:
        return {}

def save_tag_mapping(mapping, mapping_file="tag_mapping.json"):
    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

def convert_tags_list_to_int_list(tags_text):
    """
    tags_text 예: '["FPS", "Shooter", "Multiplayer"]'
    문자열을 리스트로 파싱한 후, 각 태그에 대해 고유 정수 ID를 매핑합니다.
    매핑 사전은 tag_mapping.json 파일로 관리하며, 새 태그가 있으면 새 ID를 부여합니다.
    반환값은 정수 리스트입니다.
    """
    try:
        # 태그 문자열을 리스트로 변환 (예상 형식: JSON 유사한 문자열)
        tags_list = ast.literal_eval(tags_text) if isinstance(tags_text, str) else tags_text
        if not isinstance(tags_list, list):
            tags_list = [tags_list]
    except Exception as e:
        raise Exception(f"태그 파싱 실패: {e}")

    mapping = load_tag_mapping()
    mapped_ids = []
    for tag in tags_list:
        if tag in mapping:
            mapped_ids.append(mapping[tag])
        else:
            new_id = max(mapping.values(), default=0) + 1
            mapping[tag] = new_id
            mapped_ids.append(new_id)
    save_tag_mapping(mapping)
    return mapped_ids

def upsert_scd_version(
    app_id,
    name=None,
    user_tags=None,
    price_us=None,
    releaseYear=None,
    userScore=None,
    start_date=None
):
    """
    SCD Type2 Upsert:
      - 현재 활성 레코드는 end_date가 '9999-12-31'로 표기됨.
      - 값이 변경되면 기존 활성 레코드의 end_date를 신규 레코드의 start_date 1초 전으로 업데이트 후, 신규 레코드를 Insert.
      - 값이 같으면 업데이트 없이 그대로 둠.
      - start_date: 레코드 시작 시점 (없으면 NOW() 사용).
      
    추가: user_tags가 텍스트 형태이면, 고유 태그 ID 리스트(정수 리스트)를 생성 후 JSON 문자열로 저장.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not start_date:
        start_date = now_str

    # user_tags 변환: 태그 텍스트 → 정수 ID 리스트 → JSON 문자열
    if user_tags is not None:
        try:
            int_list = convert_tags_list_to_int_list(user_tags)
            user_tags = json.dumps(int_list, ensure_ascii=False)
        except Exception as e:
            print(f"[WARN] app_id {app_id}의 user_tags 변환 실패: {e}")
            user_tags = None

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 현재 활성 레코드 조회 (end_date = '9999-12-31')
            sel_sql = """
            SELECT name, user_tags, price_us, releaseYear, userScore
              FROM TITLELIST
             WHERE app_id=%s
               AND end_date = '9999-12-31'
             ORDER BY start_date DESC
             LIMIT 1
            """
            cur.execute(sel_sql, (app_id,))
            row = cur.fetchone()

            if not row:
                # 첫 Insert
                ins_sql = """
                INSERT INTO TITLELIST
                 (app_id, name, user_tags, price_us, releaseYear, userScore,
                  start_date, end_date)
                VALUES
                 (%s, %s, %s, %s, %s, %s, %s, '9999-12-31')
                """
                cur.execute(ins_sql, (
                    app_id, name, user_tags, price_us, releaseYear, userScore, start_date
                ))
                print(f"[INSERT] app_id={app_id}, first version inserted.")
            else:
                old_name, old_tags, old_price, old_year, old_score = row
                # 기본값 처리
                if old_name is None: old_name = ""
                if old_tags is None: old_tags = ""
                if old_price is None: old_price = 0.0
                if old_year is None: old_year = ""
                if old_score is None: old_score = 0.0

                if name is None: name = ""
                if user_tags is None: user_tags = ""
                if price_us is None: price_us = 0.0
                if releaseYear is None: releaseYear = ""
                if userScore is None: userScore = 0.0

                # 값 변화 체크 (기존 user_tags는 JSON 문자열)
                changed = (
                    old_name != name or
                    str(old_tags) != str(user_tags) or
                    float(old_price) != float(price_us) or
                    old_year != releaseYear or
                    float(old_score) != float(userScore)
                )
                if changed:
                    # 기존 활성 레코드 만료: 종료 시점을 신규 레코드의 start_date 1초 전으로 계산
                    new_start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
                    new_end_date = (new_start_dt - timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
                    
                    expire_sql = """
                    UPDATE TITLELIST
                       SET end_date=%s
                     WHERE app_id=%s
                       AND end_date = '9999-12-31'
                    """
                    cur.execute(expire_sql, (new_end_date, app_id))

                    # 신규 레코드 Insert (활성 상태로 end_date는 '9999-12-31')
                    ins_sql = """
                    INSERT INTO TITLELIST
                     (app_id, name, user_tags, price_us, releaseYear, userScore,
                      start_date, end_date)
                    VALUES
                     (%s, %s, %s, %s, %s, %s, %s, '9999-12-31')
                    """
                    cur.execute(ins_sql, (
                        app_id, name, user_tags, price_us, releaseYear, userScore, start_date
                    ))
                    print(f"[UPDATE] app_id={app_id}, new version inserted.")
                else:
                    print(f"[NO CHANGE] app_id={app_id}, no update performed.")
        conn.commit()
    finally:
        conn.close()
