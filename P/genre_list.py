import requests
import json
import time
import os

# (필요하다면) 캐시나 API_KEY 설정
STEAM_API_KEY = os.getenv("STEAM_API_KEY")  # .env 활용

RATING_SCORES = {
    "overwhelmingly negative": 0,
    "very negative": 1,
    "negative": 2,
    "mostly negative": 3,
    "mixed": 4,
    "mostly positive": 5,
    "positive": 6,
    "very positive": 7,
    "overwhelmingly positive": 8
}

def fetch_storesearch_by_term(term, page=1, page_size=50):
    """
    StoreSearch API를 term 검색어로 호출하여 page 단위 결과를 반환.
    실패 시 빈 list 반환.
    """
    url = "https://store.steampowered.com/api/storesearch"
    params = {
        "term": term,
        "l": "English",
        "cc": "EN",
        "page": page,
        "count": page_size
    }

    try:
        resp = requests.get(url, params=params)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("items", [])
        else:
            print(f"[StoreSearch] HTTP {resp.status_code} Error for term={term}, page={page}")
            return []
    except Exception as e:
        print(f"[StoreSearch] Exception: {e}")
        return []

def fetch_app_details(app_id, max_retries=3):
    """
    AppDetails API 호출 (간단 버전).
    실패 시 None 반환.
    """
    url = "https://store.steampowered.com/api/appdetails"
    params = {
        "appids": app_id,
        "cc": "EN",
        "l": "English"
    }

    for attempt in range(1, max_retries+1):
        try:
            resp = requests.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data.get(str(app_id), {}).get("success", False):
                    return data[str(app_id)]["data"]
            else:
                print(f"[AppDetails] HTTP {resp.status_code} -> 재시도 {attempt}/{max_retries}")
        except Exception as e:
            print(f"[AppDetails] Exception: {e}")
        time.sleep(1)

    return None

def fetch_app_reviews(app_id, max_retries=3):
    """
    AppReviews API 호출 (간단 버전).
    실패 시 None 반환.
    """
    url = f"https://store.steampowered.com/appreviews/{app_id}"
    params = {
        "json": 1,
        "language": "all",
        "filter": "recent",
        "num_per_page": 0
    }
    for attempt in range(1, max_retries+1):
        try:
            resp = requests.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"[AppReviews] HTTP {resp.status_code} -> 재시도 {attempt}/{max_retries}")
        except Exception as e:
            print(f"[AppReviews] Exception: {e}")
        time.sleep(1)

    return None

<<<<<<< HEAD
def genre_matches(target_genre, game_genres):
    """장르 리스트 안에 target_genre(소문자)가 정확히 있는지 체크"""
    target_genre_lower = target_genre.lower()
    return any(g.strip() == target_genre_lower for g in game_genres)

# -----------------------------
# 4) 메인 로직 (모든 페이지 조회)
# -----------------------------
def get_all_games_by_genre_and_exact_rating(genre, rating="very positive", page_size=1):
    """
    genre_list에 포함된 장르(예: Indie, MOBA)를 검색어로 사용하여
    여러 페이지를 순회하며 AppDetails를 모두 모으고, 
    실제로 해당 장르가 맞는지(genres에 들어있는지) 확인 후 JSON으로 저장.
    
    이 때 페이지/아이템별 진행상황을 print로 출력해줍니다.
    """
    all_games = {}
    # 장르별로 검색
    for genre_term in genre_list:
        print(f"\n=== 장르 '{genre_term}' 수집 시작 ===")
        page = 1
        seen_app_ids = set()
        while True:
            items = fetch_storesearch_by_term(genre_term, page=page, page_size=50)
            if not items:
                print(f"'{genre_term}' 검색, page={page} 결과가 없습니다. -> 다음 장르로 이동")
                break

            print(f"[{genre_term}] page={page} 에서 {len(items)}개 검색 결과")

<<<<<<< HEAD
    page = 1
    while page<2:
        params = {
            "term": genre,
            "l": "English",
            "cc": "EN",
            "page": page,
            "count": page_size
        }
        response = requests.get(search_url, params=params)
        
        if response.status_code == 429:
            print("[StoreSearch] 429 Too Many Requests -> 30초 대기 후 재시도...")
            time.sleep(30)
            continue
        
        if response.status_code != 200:
            print(f"[StoreSearch] HTTP {response.status_code} 오류 -> 중단")
            break
        
        data = response.json()
        items = data.get("items", [])
        
        if not items:
            print(f"[종료] 더 이상 검색 결과가 없습니다. (page={page})")
            break
        
        print(f"페이지 {page} / 항목 {len(items)}개 처리...")
        
        for game in tqdm(items, desc=f"Page {page}", leave=False):
            app_id = game.get("id")
            if not app_id:
                continue
            
            if app_id in seen_app_ids:
                continue

            # (1) 캐시 + AppDetails
            game_data = fetch_app_details(app_id)
            if not game_data:
                continue
            
            # 장르 체크
            details_genres = [g.get("description", "").lower()
                              for g in game_data.get("genres", [])]
            if not genre_matches(genre, details_genres):
                continue

            # (2) 캐시 + AppReviews
            r_data = fetch_app_reviews(app_id)
            if not r_data:
                continue

            review_score_desc = r_data.get("query_summary", {}) \
                                      .get("review_score_desc", "").lower()
            current_score = RATING_SCORES.get(review_score_desc, -1)

            if current_score == target_score:
                # 가격 정보
                price_info = game_data.get("price_overview", {})
                is_free = game_data.get("is_free", False)

                filtered_games.append({
                    "app_id": app_id,
                    "name": game.get("name"),
                    "rating": review_score_desc,
                    "rating_count": r_data.get("query_summary", {}).get("total_reviews", 0),
                    "genres": details_genres,
                    "release_date": game_data.get("release_date", {}).get("date", "Unknown"),
                    "price": "Free" if is_free else price_info.get("final_formatted", "Unknown"),
                    "discount": price_info.get("discount_percent", 0) if not is_free else 0,
                    "header_image": game_data.get("header_image", ""),
                    "short_description": game_data.get("short_description", "")
                })
=======
            for i, item in enumerate(items, start=1):
                app_id = item.get("id")
                if not app_id or app_id in seen_app_ids:
                    continue
>>>>>>> f82c6a740f8443d77f6457e4003bffb8925d95d0
                seen_app_ids.add(app_id)

                # 상세 정보
                print(f"  - ({i}/{len(items)}) AppDetails 요청 중... [app_id={app_id}]")
                details = fetch_app_details(app_id)
                if not details:
                    print("    -> AppDetails 불러오기 실패, 패스")
                    continue

                # 장르 확인
                if details.get("type", "").lower() != "game":
                    # DLC나 앱 등은 패스
                    continue

                # genres 필드 내에 genre_term이 들어 있는지 확인
                # (소문자로 비교)
                genres_field = details.get("genres", [])
                genre_names = [g["description"].lower() for g in genres_field]
                if genre_term.lower() in genre_names:
                    # 해당 게임을 all_games dict에 등록(중복 제거용)
                    all_games[app_id] = {
                        "app_id": app_id,
                        "name": details.get("name"),
                        "genres": genre_names,
                        "release_date": details.get("release_date", {}).get("date", "Unknown"),
                        "is_free": details.get("is_free", False),
                        "price_overview": details.get("price_overview", {}),
                        "header_image": details.get("header_image", ""),
                        "short_description": details.get("short_description", "")
                    }
                    print(f"    -> '{details.get('name')}' 장르={genre_names}, 수집 완료")
                else:
                    print(f"    -> 장르 불일치: {genre_names}, 스킵")

            page += 1
            # API 과부하 방지 대기
            time.sleep(1)

    # 이제 all_games에 (Indie OR MOBA) 게임들이 모여 있음.
    print(f"\n[전체 장르 데이터 수집] 총 {len(all_games)}개 앱에 대해 리뷰 정보 조회 중...")
    for idx, (app_id, game_info) in enumerate(list(all_games.items()), start=1):
        print(f"  ({idx}/{len(all_games)}) 리뷰 데이터 요청 중... [app_id={app_id}]")
        reviews_data = fetch_app_reviews(app_id)
        if reviews_data and "query_summary" in reviews_data:
            score_desc = reviews_data["query_summary"].get("review_score_desc", "").lower()
            total_reviews = reviews_data["query_summary"].get("total_reviews", 0)
            all_games[app_id]["review_score_desc"] = score_desc
            all_games[app_id]["total_reviews"] = total_reviews
            print(f"    -> 리뷰 스코어: {score_desc}, 총 리뷰 수: {total_reviews}")
        else:
            # 리뷰 정보가 없으면 -1로 두는 등
            all_games[app_id]["review_score_desc"] = ""
            all_games[app_id]["total_reviews"] = 0
            print("    -> 리뷰 데이터 없음")

        time.sleep(0.2)  # API 과부하 방지 (속도 조절)

    # 최종적으로 JSON 저장
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(list(all_games.values()), f, ensure_ascii=False, indent=4)
    print(f"[완료] {output_json} 파일에 {len(all_games)}개 게임 정보 저장.")

def filter_local_games(json_path, min_rating="very positive", free_only=False, discount_only=False):
    """
    이미 다운로드된 whole_genre_data.json을 로컬에서 읽은 뒤,
    추가 조건(평점, 무료, 할인 등)에 따라 필터링.
    """
    rating_threshold = RATING_SCORES.get(min_rating.lower(), 7)  # default=Very Positive

    with open(json_path, "r", encoding="utf-8") as f:
        all_games = json.load(f)

    filtered = []
    for game in all_games:
        score_desc = game.get("review_score_desc", "")
        score_val = RATING_SCORES.get(score_desc, -1)
        if score_val < rating_threshold:
            continue

        # 무료 필터
        if free_only and not game.get("is_free", False):
            continue

        # 할인 필터
        if discount_only:
            price_info = game.get("price_overview", {})
            discount = price_info.get("discount_percent", 0)
            if discount <= 0:
                continue

        filtered.append(game)

    return filtered

if __name__ == "__main__":
    # 1) (최초/주기적으로) 전체 장르 데이터 수집
    GENRES_TO_FETCH = ["Indie", "MOBA"]
    fetch_whole_genre_data(GENRES_TO_FETCH, output_json="indie_moba_data.json")

<<<<<<< HEAD
    # 2) 검색 로직
    target_genre = "Action"
    exact_rating = "very positive"
    print(f"'{target_genre}' 장르 & 평점 '{exact_rating}' 만 검색 (모든 페이지) 중...\n")

    games = get_all_games_by_genre_and_exact_rating(
        genre=target_genre,
        rating=exact_rating,
        page_size=1
=======
    # 2) (사용자 요청 시) 로컬 JSON에서 조건 필터
    result_games = filter_local_games(
        json_path="indie_moba_data.json",
        min_rating="very positive",
        free_only=False,
        discount_only=False
>>>>>>> f82c6a740f8443d77f6457e4003bffb8925d95d0
    )

    print(f"\n필터 결과: {len(result_games)}개 게임")
    for g in result_games[:5]:  # 앞에서 5개만 예시 출력
        print(f" - {g['name']} / 평점: {g['review_score_desc']} / 장르: {g['genres']}")

