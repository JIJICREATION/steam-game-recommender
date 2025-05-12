# steam DB 에서 List 가져오는 크롤링코드 #

import requests
import json
import time

# Algolia 관련 설정 (하드코딩 대신, 환경 변수나 .env 파일로 관리하는 것이 좋음)
ALGOLIA_APP_ID = "94HE6YATEI"
ALGOLIA_API_KEY = ("MGM5MWZiMWY4NmEwZGNmMWM1ZGZhYTRiNDQ0YzIzNWViNmRlNDU1OGUxZTBmMmRhZDA3Yjg1N"
                   "zhmYWZkODYxY3ZhbGlkVW50aWw9MTc0MjU0MDI1MyZ1c2VyVG9rZW49MTU2YzUwMDc2MTAwNT"
                   "I4Y2ZiNjk2MzhlOTRjMTRlN2I%3D")

BASE_URL = (
    f"https://{ALGOLIA_APP_ID.lower()}-dsn.algolia.net/1/indexes/*/queries"
    "?x-algolia-agent=Algolia%20for%20JavaScript%20(5.21.0)%3B%20Lite%20(5.21.0)"
    "%3B%20Browser%3B%20instantsearch.js%20(4.78.0)%3B%20JS%20Helper%20(3.24.2)"
    f"&x-algolia-api-key={ALGOLIA_API_KEY}"
    f"&x-algolia-application-id={ALGOLIA_APP_ID}"
)

# 리퀘스트 세션 초기화 (Keep-Alive로 연결 재사용 가능)
#매번 새로운 TCP 커넥션 대신, 이미 맺은 연결을 재활용 → 속도 향상, 부하 감소
session = requests.Session()
session.headers.update({
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://steamdb.info/instantsearch/",
    "Origin": "https://steamdb.info"
})

def fetch_page(page, hits_per_page=50):
    """
    Algolia에 page=page, hitsPerPage=hits_per_page를 요청하여 데이터를 받는다.
    성공 시 resp.json() 반환, 실패 시 None 반환.
    """
    # 오직 1개의 request만 보냄(두 번째 요청 제거).
    # 2번째 요청(analytics=False, facetFilters 등)이 필요 없다면 삭제 가능.
    payload = {
        "requests": [
            {
                "indexName": "steamdb",
                "attributesToHighlight": ["name"],
                "attributesToRetrieve": [
                    "lastUpdated",
                    "small_capsule",
                    "name",
                    "price_us",
                    "releaseYear",
                    "userScore"
                                   ],
                "facetFilters": ["tags:Indie","tags:MOBA",["appType:Game"]],
                "facets": [
                    "appType","categories","developer","followers","hardwareCategories",
                    "languages","languagesAudio","languagesSubtitles","multiplayerCategories",
                    "price_us","publisher","releaseYear","reviews","tags","technologies","userScore"
                ],
                "highlightPostTag": "__/ais-highlight__",
                "highlightPreTag": "__ais-highlight__",
                # hitsPerPage 최적화 (50 대신 100~1000까지 가능 여부 확인)
                "hitsPerPage": hits_per_page,
                "maxValuesPerFacet": 200,
                "page": page,
                "query": ""
            }
        ]
    }

    try:
        resp = session.post(BASE_URL, json=payload, timeout=10)
        resp.raise_for_status()  # 4xx/5xx면 예외
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request failed for page={page}: {e}")
        return None

def crawl_all_pages(hits_per_page=50, delay=1.0):
    """
    nbPages를 이용해 모든 페이지를 순회하며 데이터(hits)를 수집.
    hits_per_page: 페이지 당 가져올 갯수 (최대 1000까지 가능).
    delay: 페이지 사이 대기(초).
    """
    all_hits = []
    page = 0

    while True:
        print(f"[INFO] Fetching page={page} (hitsPerPage={hits_per_page}) ...")
        data = fetch_page(page, hits_per_page=hits_per_page)
        if not data:
            print("[WARN] No data => stopping.")
            break

        results_array = data.get("results", [])
        if not results_array:
            print("[WARN] 'results' empty => stopping.")
            break

        main_result = results_array[0]
        hits = main_result.get("hits", [])
        if not hits:
            print(f"[INFO] page={page} => 0 hits => end.")
            break

        all_hits.extend(hits)
        print(f"[INFO] page={page} => {len(hits)} hits (total so far: {len(all_hits)})")

        # 전체 페이지 수 (nbPages)
        nb_pages = main_result.get("nbPages", 1)
        current_page = main_result.get("page", page)

        # 다음 페이지
        page += 1

        if page >= nb_pages:
            # 모든 페이지를 순회
            print(f"[INFO] page={page} >= nbPages={nb_pages} => all done.")
            break

        time.sleep(delay)  # API 호출 간격(초)

    return all_hits


if __name__ == "__main__":
    # hitsPerPage를 늘릴 수 있다면 100, 500, 1000 등으로 시도 가능
    # (Algolia 무료 플랜은 최대 1000까지 허용)
    HITS_PER_PAGE = 100

    # crawl_all_pages 실행
    print("[INFO] Starting crawl...")
    hits = crawl_all_pages(hits_per_page=HITS_PER_PAGE, delay=0.5)  # 딜레이를 0.5초로 줄여도 됨
    print(f"\nTotal hits: {len(hits)}")

    # 필요한 필드만 추출
    results = []
    for h in hits:
        results.append({
            "name": h.get("name"),
            "app_id": h.get("objectID"),
            "price_us": h.get("price_us"),
            "releaseYear": h.get("releaseYear"),
            "userScore": h.get("userScore")           
        })

    # JSON 파일로 저장
    filename = f"steamdb_indie_moba_{int(time.time())}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print(f"[DONE] Saved '{filename}' with {len(results)} items.")
    print("[INFO] 모든 작업이 완료되었습니다.")