import json
from datetime import datetime, timezone
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "workable_sources.json"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
BASE_URL = "https://www.workable.com/api/accounts"


def collect_workable_jobs(account):
    response = requests.get(
        f"{BASE_URL}/{account}",
        params={"details": "true"},
        headers={"User-Agent": "JobMarket-Intelligence"},
        timeout=30,
    )
    response.raise_for_status()
    jobs = response.json()["jobs"]
    if not isinstance(jobs, list) or not all(isinstance(job, dict) for job in jobs):
        raise ValueError(f"Unexpected Workable response for {account}")
    return jobs


def save_raw_snapshot(account, company, jobs):
    extracted_at = datetime.now(timezone.utc)
    snapshot = {
        "metadata": {
            "source_system": "Workable",
            "source_account": account,
            "company": company,
            "result_count": len(jobs),
            "extracted_at": extracted_at.isoformat(),
        },
        "response": {"jobs": jobs},
    }
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = extracted_at.strftime("%Y%m%d_%H%M%S_%f")
    path = RAW_DIR / f"workable_{account}_{timestamp}.json"
    temporary_path = path.with_suffix(".tmp")
    try:
        temporary_path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return path


def main():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    snapshots = [
        (source["account"], source["company"], collect_workable_jobs(source["account"]))
        for source in config["sources"]
        if source.get("enabled", True)
    ]
    for account, company, jobs in snapshots:
        path = save_raw_snapshot(account, company, jobs)
        print(f"{account}: {len(jobs)} postings saved to {path.name}")


if __name__ == "__main__":
    main()
