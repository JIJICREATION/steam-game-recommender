import requests
import time
import os
import json

# --------------------------------------------------------
# 1) Steam 전체 앱 목록 가져오기 (GetAppList)
# --------------------------------------------------------
def get_all_steam_apps():
    url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
    resp = requests.get(url)
    if resp.status_code != 200:
        print("GetAppList error:", resp.status_code)
        return []
    data = resp.json()
    apps = data.get("applist", {}).get("apps", [])
    print(f"[INFO] 전체 앱 수: {len(apps)}")
    return apps

# --------------------------------------------------------
# 2) 리뷰 점수 조회 함수 (appreviews)
# --------------------------------------------------------
def get_review_score_desc(appid, backoff=30):
    """
    해당 appid의 리뷰 평점(review_score_desc)을 반환.
    HTTP 429가 발생하면 backoff초 동안 대기 후 한 번 재시도함.
    """
    url = f"https://store.steampowered.com/appreviews/{appid}"
    params = {
        "json": 1,
        "language": "all",
        "filter": "recent",
        "num_per_page": 0
    }
    resp = requests.get(url, params=params)
    
    if resp.status_code == 429:
        print(f"[WARN] 429 Too Many Requests (appreviews) - appid={appid}, 대기 {backoff}초")
        time.sleep(backoff)
        # 재시도
        resp = requests.get(url, params=params)
        if resp.status_code == 429:
            print("[ERROR] 재시도에도 429 발생. 더 길게 대기하거나 로직을 개선해야 함.")
            return None
    
    if resp.status_code != 200:
        print(f"[ERROR] appreviews({appid}) HTTP {resp.status_code}")
        return None
    
    jdata = resp.json()
    desc = jdata.get("query_summary", {}).get("review_score_desc", None)
    return desc

# --------------------------------------------------------
# 3) appdetails 호출로 장르, type=game 여부 확인
# --------------------------------------------------------
def get_appdetails(appid, backoff=30):
    """
    해당 appid의 appdetails 결과(장르, type 등)를 반환.
    """
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
    resp = requests.get(url)
    
    if resp.status_code == 429:
        print(f"[WARN] 429 Too Many Requests (appdetails) - appid={appid}, 대기 {backoff}초")
        time.sleep(backoff)
        resp = requests.get(url)
        if resp.status_code == 429:
            print("[ERROR] 재시도에도 429 발생. 더 길게 대기하거나 로직을 개선해야 함.")
            return None
    
    if resp.status_code != 200:
        print(f"[ERROR] appdetails({appid}) HTTP {resp.status_code}")
        return None
    
    data = resp.json().get(str(appid), {})
    if not data.get("success", False):
        return None
    
    return data.get("data", {})

# --------------------------------------------------------
# 4) 대량 처리 시 중간 저장/재개를 위한 함수
# --------------------------------------------------------
def load_partial_results(filename="partial_results.json"):
    """
    중간 저장된 결과를 로드하고, {appid: {...}} 형태로 반환
    """
    if not os.path.exists(filename):
        return {}
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_partial_results(data, filename="partial_results.json"):
    """
    중간 결과 {appid: {...}} 를 JSON 파일로 저장
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --------------------------------------------------------
# 5) 메인 처리 로직
# --------------------------------------------------------
def get_very_positive_games_by_genre(
    target_genre="Action", 
    chunk_size=5000,  # 한 번에 처리할 앱 개수
    resume_file="partial_results.json"
):
    """
    1) 전체 앱 리스트를 chunk로 나눠 순회
    2) appdetails -> 장르 & type='game' 여부 확인
    3) appreviews -> 'Very Positive' 여부 확인
    4) 중간 결과를 {appid: {...}} 형태로 partial_results.json 에 저장
       - 나중에 재실행하면 이미 처리된 appid는 건너뛸 수 있음
    """
    all_apps = get_all_steam_apps()
    partial = load_partial_results(resume_file)  # 이전 실행 기록 로드
    
    # 최종 결과(조건 만족)
    final_results = {}
    # 이미 partial에 저장된 (성공/실패) 앱 ID를 중복 처리하지 않기 위함
    processed_ids = set(partial.keys())
    
    # apps를 chunk_size 단위로 자르기
    for start_idx in range(0, len(all_apps), chunk_size):
        end_idx = start_idx + chunk_size
        chunk = all_apps[start_idx:end_idx]
        
        print(f"\n[INFO] Chunk {start_idx}~{end_idx} / 총 {len(all_apps)}")
        
        for app in chunk:
            appid = str(app["appid"])
            name = app["name"]
            
            # 이미 처리된 appid면 스킵
            if appid in processed_ids:
                # partial에서 가져온 상태가 'skip'/'VP' 등일 수 있으므로,
                # 만약 partial[appid]가 'VP'라면 final_results에 추가 가능
                info = partial[appid]
                if info.get("result") == "VP":
                    final_results[appid] = info
                continue
            
            # 1) appdetails 조회
            detail_data = get_appdetails(appid)
            time.sleep(0.3)  # 호출 간 딜레이
            
            if not detail_data:
                # 실패하거나 success=False
                partial[appid] = {"result": "fail", "name": name}
                continue
            
            if detail_data.get("type") != "game":
                partial[appid] = {"result": "skip_not_game", "name": name}
                continue
            
            # 장르 체크
            genres = detail_data.get("genres", [])
            genre_names = [g["description"].lower() for g in genres if "description" in g]
            if target_genre.lower() not in " ".join(genre_names):
                partial[appid] = {"result": "skip_wrong_genre", "name": name}
                continue
            
            # 2) review_score_desc 조회
            score_desc = get_review_score_desc(appid)
            time.sleep(0.3)  # 호출 간 딜레이
            
            if score_desc and score_desc.lower() == "very positive":
                # 조건 만족
                final_results[appid] = {
                    "appid": appid,
                    "name": name,
                    "genres": genre_names,
                    "review_score_desc": score_desc,
                    "result": "VP"
                }
                partial[appid] = final_results[appid]
            else:
                partial[appid] = {
                    "result": "skip_review",
                    "name": name,
                    "review_score_desc": score_desc
                }
            
            # 처리 후 partial 저장 (예: 100개 단위로)
            if len(partial) % 100 == 0:
                save_partial_results(partial, resume_file)
        
        # chunk 끝날 때 partial 저장
        save_partial_results(partial, resume_file)
    
    # 모든 chunk 끝나면 final_results 정리
    print(f"\n[INFO] '{target_genre}' & Very Positive 게임 수: {len(final_results)}")
    return final_results


def save_final_games(games, filename="very_positive_games.json"):
    """
    최종 결과(조건 만족 게임들)만 별도 JSON으로 저장
    games: {appid: {...}}
    """
    # dictionary -> list 변환
    result_list = list(games.values())
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result_list, f, ensure_ascii=False, indent=4)
    print(f"[INFO] 최종 {len(result_list)}개 결과를 '{filename}'에 저장했습니다.")


if __name__ == "__main__":
    # 실행 예시:
    # 특정 장르 예: "Action", "RPG", "Strategy" ...
    TARGET_GENRE = "Action"

    # (1) 실행
    vp_games = get_very_positive_games_by_genre(
        target_genre=TARGET_GENRE,
        chunk_size=5000, 
        resume_file="partial_results.json"  # 중간 결과 저장 파일
    )
    
    # (2) 최종 결과 저장
    save_final_games(vp_games, filename="very_positive_games.json")

    # (3) 간단 출력
    print("\n===== 예시 출력 (상위 10개) =====")
    some_items = list(vp_games.values())[:10]
    for idx, item in enumerate(some_items, start=1):
        print(f"{idx}. {item.get('name')} (AppID={item.get('appid')}, Review={item.get('review_score_desc')})")
    print("==================================")