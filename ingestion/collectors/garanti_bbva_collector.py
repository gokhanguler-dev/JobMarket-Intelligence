import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

BASE_URL = "https://kariyer.garantibbva.com.tr"
LIST_URL = f"{BASE_URL}/tum-kariyer-firsatlari"

SOURCE_SYSTEM = "GarantiBBVA"
COMPANY_NAME = "Garanti BBVA"

REQUEST_TIMEOUT = 30
REQUEST_DELAY_SECONDS = 0.3


def get_session():
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/155.0.0.0 Safari/537.36"
            )
        }
    )

    return session


def clean_text(value):
    if not value:
        return None

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def extract_job_links(session):
    response = session.get(
        LIST_URL,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    links = set()

    for anchor in soup.find_all("a", href=True):
        url = urljoin(
            LIST_URL,
            anchor.get("href")
        )

        parsed = urlparse(url)

        if (
            parsed.netloc == "kariyer.garantibbva.com.tr"
            and parsed.path.startswith("/ilan/")
        ):
            links.add(url)

    return sorted(links)


def extract_source_job_id(job_url):
    """
    Example:

    /ilan/R00000007457/0000007374/veri-bilimi---data-scientist

    SourceJobID:
    R00000007457_0000007374
    """

    path_parts = [
        part
        for part in urlparse(job_url).path.split("/")
        if part
    ]

    if len(path_parts) < 3:
        return None

    requisition_id = path_parts[1]
    advert_id = path_parts[2]

    return f"{requisition_id}_{advert_id}"


def parse_job_detail(session, job_url):
    response = session.get(
        job_url,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    source_job_id = extract_source_job_id(
        job_url
    )

    # Page title / H1
    h1 = soup.find("h1")

    title = clean_text(
        h1.get_text(" ", strip=True)
        if h1
        else None
    )

    # Keep a clean full-page text in RAW.
    # We can build more precise field-specific parsing after
    # inspecting the first snapshot.
    page_text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    return {
        "source_job_id": source_job_id,
        "title": title,
        "company": COMPANY_NAME,
        "job_url": job_url,
        "full_text": page_text
    }


def save_raw_snapshot(jobs):
    extracted_at = datetime.now(
        timezone.utc
    )

    payload = {
        "metadata": {
            "source_system": SOURCE_SYSTEM,
            "company": COMPANY_NAME,
            "source_url": LIST_URL,
            "result_count": len(jobs),
            "extracted_at": extracted_at.isoformat()
        },
        "response": {
            "jobs": jobs
        }
    }

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    timestamp = extracted_at.strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        f"garanti_bbva_{timestamp}.json"
    )

    filepath = RAW_DIR / filename

    with open(
        filepath,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2
        )

    return filepath


def main():
    print("=" * 65)
    print("GARANTI BBVA JOB COLLECTOR")
    print("=" * 65)

    session = get_session()

    print("\nCollecting job listing...")

    job_links = extract_job_links(
        session
    )

    print(
        f"Job links found : {len(job_links)}"
    )

    jobs = []
    failed = 0

    for index, job_url in enumerate(
        job_links,
        start=1
    ):
        try:
            job = parse_job_detail(
                session,
                job_url
            )

            jobs.append(job)

            print(
                f"[{index:02d}/{len(job_links):02d}] "
                f"OK - {job['title']}"
            )

        except Exception as exc:
            failed += 1

            print(
                f"[{index:02d}/{len(job_links):02d}] "
                f"FAILED - {job_url}"
            )

            print(
                f"    {exc}"
            )

        time.sleep(
            REQUEST_DELAY_SECONDS
        )

    filepath = save_raw_snapshot(
        jobs
    )

    print("\n" + "=" * 65)
    print("COLLECTION COMPLETED")
    print(f"Jobs found     : {len(job_links)}")
    print(f"Jobs collected : {len(jobs)}")
    print(f"Jobs failed    : {failed}")
    print(f"RAW saved      : {filepath.name}")
    print("=" * 65)


if __name__ == "__main__":
    main()