



"""
이 스크립트는 MariaDB의 'REVIEW_TAG' 테이블에 'app_id', 'review_text' 컬럼을 추가하고,
'GAME_REVIEW' 테이블의 데이터를 이용하여 두 컬럼을 업데이트합니다.

[작업 순서]
1. REVIEW_TAG 테이블에 'app_id' 컬럼 추가 (이미 존재하면 생략)
2. REVIEW_TAG 테이블에 'review_text' 컬럼 추가 (이미 존재하면 생략)
3. GAME_REVIEW의 'app_id', 'review_text'로 REVIEW_TAG를 업데이트

[데이터베이스 정보]
- DB: steam_lit_project (MariaDB)
- 문자셋/콜레이션: utf8mb4 / utf8mb4_general_ci
"""






import mysql.connector

# 연결 객체를 초기화합니다.
conn = None

def column_exists(cursor, table_name, column_name):
    
    query = """
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s;
    """
    cursor.execute(query, (table_name, column_name))
    result = cursor.fetchone()
    return result[0] > 0

try:
    # MariaDB 연결 정보 (init_command를 사용하여 문자셋/콜레이션 설정)
    conn = mysql.connector.connect(
        host="bootcampproject2t1steam.cdi60g8ggh0i.ap-southeast-2.rds.amazonaws.com",
        port=3306,
        user="minsung",
        password="password",
        database="steam_lit_project",
        charset="utf8mb4",
        collation="utf8mb4_general_ci",  # 기본 콜레이션을 명시적으로 지정
        use_pure=True,
        init_command="SET NAMES 'utf8mb4' COLLATE 'utf8mb4_general_ci';"
    )
    print("DB 연결 및 문자셋/콜레이션 설정 완료.")
    
    with conn.cursor() as cursor:
        # 1. REVIEW_TAG 테이블에 app_id 컬럼을 id 컬럼 뒤에 추가 (이미 존재하면 건너뜀)
        if not column_exists(cursor, 'REVIEW_TAG', 'app_id'):
            try:
                alter_query = "ALTER TABLE REVIEW_TAG ADD COLUMN app_id INT AFTER id;"
                cursor.execute(alter_query)
                conn.commit()
                print("app_id 컬럼 추가 완료.")
            except Exception as e:
                print("app_id 컬럼 추가 오류:", e)
        else:
            print("app_id 컬럼이 이미 존재합니다.")
        
        # 2. REVIEW_TAG 테이블에 review_text 컬럼을 맨 끝에 추가 (이미 존재하면 건너뜀)
        if not column_exists(cursor, 'REVIEW_TAG', 'review_text'):
            try:
                alter_query = "ALTER TABLE REVIEW_TAG ADD COLUMN review_text TEXT;"
                cursor.execute(alter_query)
                conn.commit()
                print("review_text 컬럼 추가 완료.")
            except Exception as e:
                print("review_text 컬럼 추가 오류:", e)
        else:
            print("review_text 컬럼이 이미 존재합니다.")
        
        # 3. GAME_REVIEW 테이블에서 review_id에 대응하는 app_id와 review_text를 가져와 REVIEW_TAG 업데이트
        update_query = """
        UPDATE REVIEW_TAG rt
        JOIN GAME_REVIEW gr ON rt.review_id = gr.review_id
        SET rt.app_id = gr.app_id,
            rt.review_text = gr.review_text;
        """
        try:
            cursor.execute(update_query)
            conn.commit()
            print("REVIEW_TAG 테이블 업데이트 완료.")
        except Exception as e:
            print("REVIEW_TAG 업데이트 오류:", e)
            
except mysql.connector.Error as err:
    print("MySQL 연결 오류:", err)
    
finally:
    if conn is not None and conn.is_connected():
        conn.close()
        print("DB 연결 종료.")
