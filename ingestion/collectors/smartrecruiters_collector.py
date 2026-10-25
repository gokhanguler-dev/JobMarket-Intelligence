import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = BASE_DIR / "config" / "smartrecruiters_sources.json"
RAW_DIR = BASE_DIR / "data" / "raw"

BASE_URL = "https://api.smartrecruiters.com/v1/companies"

PAGE_LIMIT = 100
REQUEST_TIMEOUT = 30
DETAIL_DELAY_SECONDS = 0.15


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_source(session, source):
    company = source["company"]
    company_identifier = source["company_identifier"]
    country = source.get("country", "tr")

    print("=" * 70)
    print(f"[START] SmartRecruiters source: {company}")
    print("=" * 70)

    list_url = f"{BASE_URL}/{company_identifier}/postings"

    offset = 0
    summaries = []

    while True:
        params = {
            "limit": PAGE_LIMIT,
            "offset": offset,
            "country": country,
        }

        response = session.get(
            list_url,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        payload = response.json()

        page_jobs = payload.get("content", [])
        total_found = payload.get("totalFound", 0)

        summaries.extend(page_jobs)

        print(
            f"[LIST] offset={offset} "
            f"page={len(page_jobs)} "
            f"collected={len(summaries)} "
            f"total={total_found}"
        )

        if not page_jobs:
            break

        if len(summaries) >= total_found:
            break

        offset += PAGE_LIMIT

    jobs = []
    failed_details = []

    for index, summary in enumerate(summaries, start=1):
        posting_id = summary.get("id")

        if not posting_id:
            failed_details.append(
                {
                    "posting_id": None,
                    "reason": "Missing posting id",
                }
            )
            continue

        detail_url = (
            f"{BASE_URL}/"
            f"{company_identifier}/postings/{posting_id}"
        )

        try:
            response = session.get(
                detail_url,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            detail = response.json()

            jobs.append(
                {
                    "summary": summary,
                    "detail": detail,
                }
            )

            print(
                f"[DETAIL] {index}/{len(summaries)} "
                f"{posting_id} | OK"
            )

        except Exception as exc:
            failed_details.append(
                {
                    "posting_id": posting_id,
                    "reason": str(exc),
                }
            )

            print(
                f"[DETAIL] {index}/{len(summaries)} "
                f"{posting_id} | FAILED | {exc}"
            )

        time.sleep(DETAIL_DELAY_SECONDS)

    extracted_at = datetime.now(timezone.utc).isoformat()

    output = {
        "metadata": {
            "source_system": "SmartRecruiters",
            "source_platform": "SmartRecruiters",
            "company": company,
            "company_identifier": company_identifier,
            "country": country,
            "result_count": len(summaries),
            "detail_count": len(jobs),
            "failed_detail_count": len(failed_details),
            "extracted_at": extracted_at,
        },
        "response": {
            "jobs": jobs,
            "failed_details": failed_details,
        },
    }

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    safe_identifier = (
        company_identifier
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )

    output_path = (
        RAW_DIR
        / f"smartrecruiters_{safe_identifier}_{timestamp}.json"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(f"[DONE] {company}")
    print(f"List jobs      : {len(summaries)}")
    print(f"Detail jobs    : {len(jobs)}")
    print(f"Failed details : {len(failed_details)}")
    print(f"Raw file       : {output_path.name}")

    return output_path


def main():
    config = load_config()

    sources = [
        source
        for source in config.get("sources", [])
        if source.get("enabled", True)
    ]

    session = requests.Session()

    session.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": "JobMarket-Intelligence/1.0",
        }
    )

    successful_sources = 0
    failed_sources = 0

    for source in sources:
        company = source.get("company", "Unknown")

        try:
            collect_source(session, source)
            successful_sources += 1

        except Exception as exc:
            failed_sources += 1

            print()
            print(
                f"[ERROR] Source failed: "
                f"{company} | {exc}"
            )

    print()
    print("=" * 70)
    print("[SUMMARY]")
    print(f"Successful sources: {successful_sources}")
    print(f"Failed sources: {failed_sources}")
    print("=" * 70)


if __name__ == "__main__":
    main()