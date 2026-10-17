import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

BASE_API_URL = "https://api.akbank.com/api/v1/crm/candidateportal"

LIST_URL = f"{BASE_API_URL}/advert/list"
DETAIL_URL = f"{BASE_API_URL}/advert/detail"

SOURCE_SYSTEM = "Akbank"
COMPANY_NAME = "Akbank"

REQUEST_TIMEOUT = 30
REQUEST_DELAY_SECONDS = 0.2


def get_session():
    session = requests.Session()

    session.headers.update(
        {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://kariyer.akbank.com",
            "Referer": "https://kariyer.akbank.com/",
        }
    )

    return session


def get_job_list(session):
    response = session.post(
        LIST_URL,
        json={},
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    data = response.json()

    if not isinstance(data, list):
        raise ValueError(
            "Akbank advert/list response is not a list."
        )

    return data


def get_job_detail(session, job_id):
    response = session.post(
        DETAIL_URL,
        json={
            "id": job_id
        },
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    return response.json()


def collect_jobs(session):
    job_list = get_job_list(session)

    print(f"Jobs returned : {len(job_list)}")

    jobs = []
    failed = 0

    for index, list_job in enumerate(
        job_list,
        start=1,
    ):
        job_id = list_job.get("id")
        title = list_job.get("title")

        try:
            detail = get_job_detail(
                session,
                job_id,
            )

            # Keep both representations.
            #
            # "list" contains useful discovery/lifecycle metadata.
            # "detail" contains the full description and qualifications.
            jobs.append(
                {
                    "source_job_id": job_id,
                    "company": COMPANY_NAME,
                    "job_url": (
                        "https://kariyer.akbank.com/"
                        f"shared/advert-list/{job_id}"
                    ),
                    "list": list_job,
                    "detail": detail,
                }
            )

            print(
                f"[{index:02d}/{len(job_list):02d}] "
                f"OK - {title}"
            )

        except Exception as exc:
            failed += 1

            print(
                f"[{index:02d}/{len(job_list):02d}] "
                f"FAILED - {title}"
            )

            print(
                f"    {exc}"
            )

        time.sleep(
            REQUEST_DELAY_SECONDS
        )

    return jobs, failed, len(job_list)


def save_raw_snapshot(
    jobs,
    source_count,
    failed,
):
    extracted_at = datetime.now(
        timezone.utc
    )

    payload = {
        "metadata": {
            "source_system": SOURCE_SYSTEM,
            "company": COMPANY_NAME,
            "list_endpoint": LIST_URL,
            "detail_endpoint": DETAIL_URL,
            "source_count": source_count,
            "collected_count": len(jobs),
            "failed_count": failed,
            "extracted_at": extracted_at.isoformat(),
        },
        "response": {
            "jobs": jobs
        },
    }

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = extracted_at.strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        f"akbank_{timestamp}.json"
    )

    filepath = RAW_DIR / filename

    with open(
        filepath,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return filepath


def main():
    print("=" * 65)
    print("AKBANK JOB COLLECTOR")
    print("=" * 65)

    session = get_session()

    print("\nCollecting active job list...")

    jobs, failed, source_count = collect_jobs(
        session
    )

    filepath = save_raw_snapshot(
        jobs,
        source_count,
        failed,
    )

    print("\n" + "=" * 65)
    print("COLLECTION COMPLETED")
    print(f"Jobs returned  : {source_count}")
    print(f"Jobs collected : {len(jobs)}")
    print(f"Jobs failed    : {failed}")
    print(f"RAW saved      : {filepath.name}")
    print("=" * 65)


if __name__ == "__main__":
    main()