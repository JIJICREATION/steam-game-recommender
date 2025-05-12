# main.py ( DB에 적재 및 Json 파일로 보관)

import json
import os

from db_utils import fetch_app_ids, update_app_tags
from tags_crawler import fetch_tags_via_plus_button

def stage1_save_to_json(json_path="tags_stage1.json"):
    """
    1) DB에서 app_id 목록
    2) 각각 태그 크롤링
    3) 결과를 로컬 JSON에 저장
    """
    app_ids = fetch_app_ids()
    print(f"[INFO] {len(app_ids)}개 app_id: {app_ids}")

    results = []
    for i, app_id in enumerate(app_ids, start=1):
        print(f"\n[{i}/{len(app_ids)}] app_id={app_id}: 태그 수집")
        data = fetch_tags_via_plus_button(app_id)
        results.append(data)

    # 로컬 JSON 저장
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print(f"[DONE] {json_path}에 {len(results)}개 결과 저장")

def stage2_update_db_from_json(json_path="tags_stage1.json"):
    """
    stage1에서 만든 JSON 파일을 읽어,
    DB의 LIST_OF_MOBA_INDI.user_tags에 반영
    """
    with open(json_path, "r", encoding="utf-8") as f:
        all_data = json.load(f)

    for i, entry in enumerate(all_data, start=1):
        app_id = entry.get("app_id")
        tags = entry.get("user_tags", [])
        tags_json = json.dumps(tags, ensure_ascii=False)

        update_app_tags(app_id, tags_json)
        print(f"[INFO] DB update app_id={app_id}, 태그 {len(tags)}개")

    print("[DONE] DB 반영 완료")

def main():
    """
    1) stage1: 크롤링 + 로컬 JSON 저장
    2) stage2: JSON을 다시 읽어 DB 저장
    """
    # (A) 크롤링 & JSON
    json_file = "tags_stage1.json"
    stage1_save_to_json(json_file)

    # (B) DB 적재
    stage2_update_db_from_json(json_file)

if __name__ == "__main__":
    main()
