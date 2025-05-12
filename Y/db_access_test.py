import mariadb
import sys

# MariaDB 연결 설정
try:
    conn = mariadb.connect(
        host="bootcampproject2t1steam.cdi60g8ggh0i.ap-southeast-2.rds.amazonaws.com",  # RDS 엔드포인트
        port=3306,  # 포트 번호
        user="minsung",  # 사용자 이름
        password="password",  # 비밀번호 (AWS RDS 설정 시 지정한 비밀번호)
    )
    print("Successfully connected to the database!")

    # 커서 생성
    cur = conn.cursor()

    # SQL 실행 예제: 데이터베이스 목록 조회
    cur.execute("SHOW DATABASES")
    for db in cur:
        print(db)

except mariadb.Error as e:
    print(f"Error connecting to MariaDB: {e}")
    sys.exit(1)

finally:
    # 연결 종료
    if conn:
        conn.close()
