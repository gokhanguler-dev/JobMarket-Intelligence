import json
from datetime import datetime, timezone
from pathlib import Path

import requests


BASE_URL = "https://boards-api.greenhouse.io/v1/boards"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "greenhouse_sources.json"
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def collect_greenhouse_jobs(board_token):
    url = f"{BASE_URL}/{board_token}/jobs"

    response = requests.get(
        url,
        params={"content": "true"},
        timeout=30
    )

    response.raise_for_status()

    payload = response.json()

    return payload.get("jobs", [])


def save_raw_snapshot(board_token, company, jobs):
    extracted_at = datetime.now(timezone.utc)

    payload = {
        "metadata": {
            "source_system": "Greenhouse",
            "source_board": board_token,
            "company": company,
            "result_count": len(jobs),
            "extracted_at": extracted_at.isoformat()
        },
        "response": {
            "jobs": jobs
        }
    }

    timestamp = extracted_at.strftime("%Y%m%d_%H%M%S")

    filename = f"greenhouse_{board_token}_{timestamp}.json"
    filepath = RAW_DIR / filename

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2
        )

    return filepath


def main():
    config = load_config()

    total_jobs = 0
    successful_sources = 0
    failed_sources = 0

    print("=" * 60)
    print("GREENHOUSE JOB COLLECTOR")
    print("=" * 60)

    for source in config["sources"]:

        if not source.get("enabled", True):
            continue

        board_token = source["board_token"]
        company = source["company"]

        print(f"\nCollecting: {company}")
        print(f"Greenhouse board: {board_token}")

        try:
            jobs = collect_greenhouse_jobs(board_token)

            filepath = save_raw_snapshot(
                board_token=board_token,
                company=company,
                jobs=jobs
            )

            print(f"Jobs returned : {len(jobs)}")
            print(f"RAW saved     : {filepath.name}")

            total_jobs += len(jobs)
            successful_sources += 1

        except Exception as exc:
            failed_sources += 1

            print(f"FAILED        : {exc}")

    print("\n" + "=" * 60)
    print("COLLECTION COMPLETED")
    print(f"Sources OK    : {successful_sources}")
    print(f"Sources failed: {failed_sources}")
    print(f"Jobs returned : {total_jobs}")
    print("=" * 60)


if __name__ == "__main__":
    main()