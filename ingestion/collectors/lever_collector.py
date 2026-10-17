import json
from datetime import datetime, timezone
from pathlib import Path

import requests


BASE_URL = "https://api.lever.co/v0/postings"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "lever_sources.json"
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def collect_lever_jobs(site):
    url = f"{BASE_URL}/{site}"

    response = requests.get(
        url,
        params={"mode": "json"},
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def save_raw_snapshot(site, company, jobs):
    extracted_at = datetime.now(timezone.utc)

    payload = {
        "metadata": {
            "source_system": "Lever",
            "source_site": site,
            "company": company,
            "result_count": len(jobs),
            "extracted_at": extracted_at.isoformat()
        },
        "response": {
            "jobs": jobs
        }
    }

    timestamp = extracted_at.strftime("%Y%m%d_%H%M%S")

    filename = f"lever_{site}_{timestamp}.json"
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
    print("LEVER JOB COLLECTOR")
    print("=" * 60)

    for source in config["sources"]:

        if not source.get("enabled", True):
            continue

        site = source["site"]
        company = source["company"]

        print(f"\nCollecting: {company}")
        print(f"Lever site: {site}")

        try:
            jobs = collect_lever_jobs(site)

            filepath = save_raw_snapshot(
                site=site,
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