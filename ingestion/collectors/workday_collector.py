import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

CONFIG_PATH = BASE_DIR / "config" / "workday_sources.json"
RAW_DIR = BASE_DIR / "data" / "raw"

RAW_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

PAGE_LIMIT = 20
REQUEST_TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/155.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Content-Type": "application/json",
}


# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------

def load_sources():
    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        config = json.load(file)

    return [
        source
        for source in config.get("sources", [])
        if source.get("enabled", True)
    ]


# ---------------------------------------------------------
# URL HELPERS
# ---------------------------------------------------------

def build_base_url(source):
    return f"https://{source['host']}"


def build_jobs_url(source):
    return (
        f"{build_base_url(source)}"
        f"/wday/cxs/{source['tenant']}/{source['site']}/jobs"
    )


def build_detail_url(source, external_path):
    return (
        f"{build_base_url(source)}"
        f"/wday/cxs/{source['tenant']}/{source['site']}"
        f"{external_path}"
    )


# ---------------------------------------------------------
# LIST API
# ---------------------------------------------------------

def fetch_job_page(session, source, offset):
    url = build_jobs_url(source)

    payload = {
        "appliedFacets": {
            "locations": source.get("location_facets", [])
        },
        "limit": PAGE_LIMIT,
        "offset": offset,
        "searchText": "",
    }

    response = session.post(
        url,
        json=payload,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    return response.json()


def fetch_all_job_summaries(session, source):
    jobs = []
    offset = 0
    total = None

    while True:
        data = fetch_job_page(
            session=session,
            source=source,
            offset=offset,
        )

        batch = data.get("jobPostings", [])

        if total is None:
            total = data.get("total", 0)

            print(
                f"[INFO] {source['company']} "
                f"total jobs: {total}"
            )

        print(
            f"[INFO] {source['company']} "
            f"offset={offset} "
            f"batch={len(batch)}"
        )

        if not batch:
            break

        jobs.extend(batch)

        offset += PAGE_LIMIT

        if offset >= total:
            break

    return jobs


# ---------------------------------------------------------
# DETAIL API
# ---------------------------------------------------------

def fetch_job_detail(session, source, external_path):
    url = build_detail_url(
        source=source,
        external_path=external_path,
    )

    response = session.get(
        url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    return response.json()


# ---------------------------------------------------------
# SOURCE COLLECTION
# ---------------------------------------------------------

def collect_source(source):
    company = source["company"]

    print()
    print("=" * 70)
    print(f"[START] Workday source: {company}")
    print("=" * 70)

    extracted_at = datetime.now(timezone.utc).isoformat()

    session = requests.Session()

    summaries = fetch_all_job_summaries(
        session=session,
        source=source,
    )

    jobs = []
    failed_details = []

    for index, summary in enumerate(summaries, start=1):
        external_path = summary.get("externalPath")

        if not external_path:
            print(
                f"[WARN] Missing externalPath: "
                f"{summary.get('title')}"
            )
            continue

        try:
            detail_response = fetch_job_detail(
                session=session,
                source=source,
                external_path=external_path,
            )

            job_posting_info = detail_response.get(
                "jobPostingInfo",
                {}
            )

            jobs.append(
                {
                    "summary": summary,
                    "jobPostingInfo": job_posting_info,
                }
            )

            print(
                f"[DETAIL] "
                f"{index}/{len(summaries)} "
                f"{summary.get('title')}"
            )

        except requests.RequestException as exc:
            failed_details.append(
                {
                    "title": summary.get("title"),
                    "externalPath": external_path,
                    "error": str(exc),
                }
            )

            print(
                f"[ERROR] Detail failed: "
                f"{summary.get('title')} | {exc}"
            )

        # Small delay so we do not hammer the source.
        time.sleep(0.15)

    result = {
        "metadata": {
            "source_system": "Workday",
            "source_platform": "Workday",
            "company": company,
            "tenant": source["tenant"],
            "site": source["site"],
            "host": source["host"],
            "country": source.get("country"),
            "location_name": source.get("location_name"),
            "location_facets": source.get(
                "location_facets",
                [],
            ),
            "list_result_count": len(summaries),
            "detail_result_count": len(jobs),
            "failed_detail_count": len(failed_details),
            "extracted_at": extracted_at,
        },
        "jobs": jobs,
        "failed_details": failed_details,
    }

    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%d_%H%M%S")

    safe_tenant = (
        source["tenant"]
        .lower()
        .replace(" ", "_")
    )

    output_path = (
        RAW_DIR
        / f"workday_{safe_tenant}_{timestamp}.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(f"[DONE] {company}")
    print(
        f"[INFO] List jobs: "
        f"{len(summaries)}"
    )
    print(
        f"[INFO] Detail jobs: "
        f"{len(jobs)}"
    )
    print(
        f"[INFO] Failed details: "
        f"{len(failed_details)}"
    )
    print(
        f"[INFO] Raw file: "
        f"{output_path.name}"
    )

    return result


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():
    sources = load_sources()

    print(
        f"[INFO] Enabled Workday sources: "
        f"{len(sources)}"
    )

    if not sources:
        print(
            "[WARN] No enabled Workday sources "
            "found."
        )
        return

    successful_sources = 0
    failed_sources = 0

    for source in sources:
        try:
            collect_source(source)
            successful_sources += 1

        except Exception as exc:
            failed_sources += 1

            print()
            print(
                f"[ERROR] Source failed: "
                f"{source.get('company')} | {exc}"
            )

    print()
    print("=" * 70)
    print("[SUMMARY]")
    print(
        f"Successful sources: "
        f"{successful_sources}"
    )
    print(
        f"Failed sources: "
        f"{failed_sources}"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()