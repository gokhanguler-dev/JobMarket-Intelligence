import json
from contextlib import closing
from datetime import timezone

from ingestion.collectors.workable_collector import RAW_DIR
from ingestion.loaders.dwh_loader import get_connection
from ingestion.loaders.greenhouse_raw_loader import clean_html_text
from ingestion.loaders.lever_raw_loader import parse_iso_datetime


TURKEY_COUNTRIES = {"tr", "tur", "turkey", "türkiye", "turkiye"}


def turkey_location(job):
    locations = job.get("locations") or []
    for location in locations:
        if location.get("hidden"):
            continue
        country_code = (location.get("countryCode") or "").casefold()
        country = (location.get("country") or "").strip().casefold().replace("\u0307", "")
        if country_code == "tr" or country in TURKEY_COUNTRIES:
            city = location.get("city") or location.get("region")
            return f"{city}, Turkey" if city else "Turkey"

    if (job.get("country") or "").strip().casefold().replace("\u0307", "") in TURKEY_COUNTRIES:
        city = job.get("city") or job.get("state")
        return f"{city}, Turkey" if city else "Turkey"

    return None


def load_file(cursor, path):
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    metadata = snapshot["metadata"]
    account = metadata["source_account"]
    company = metadata["company"]
    extracted_at = parse_iso_datetime(metadata["extracted_at"])
    inserted = 0
    skipped = 0

    for job in snapshot["response"]["jobs"]:
        location = turkey_location(job)
        shortcode = job.get("shortcode")
        title = job.get("title")
        link = job.get("shortlink") or job.get("url")
        if not all((location, shortcode, title, link)):
            skipped += 1
            continue

        source_job_id = f"{account}:{shortcode}"
        description = clean_html_text(job.get("description"))
        published_at = parse_iso_datetime(job.get("published_on") or job.get("created_at"))
        if published_at is not None and published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)

        cursor.execute(
            """
            INSERT INTO stg.JobPostingRaw (
                SourceJobID, SourceSystem, SourcePlatform, Source, Company,
                JobTitle, JobLocation, Snippet, Description, EmploymentType,
                WorkModel, JobLink, SourceCreatedAt, ExtractedAt, RawFileName
            )
            SELECT ?, 'Workable', 'Workable', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            WHERE NOT EXISTS (
                SELECT 1
                FROM stg.JobPostingRaw WITH (UPDLOCK, HOLDLOCK)
                WHERE SourceSystem = 'Workable'
                  AND SourceJobID = ?
                  AND RawFileName = ?
            );
            """,
            source_job_id,
            account,
            company,
            title,
            location,
            description,
            description,
            job.get("employment_type") or None,
            "Remote" if job.get("telecommuting") is True else None,
            link,
            published_at,
            extracted_at,
            path.name,
            source_job_id,
            path.name,
        )
        inserted += cursor.rowcount

    return inserted, skipped


def main():
    files = sorted(RAW_DIR.glob("workable_*.json"))
    if not files:
        print("No Workable RAW files found.")
        return

    with closing(get_connection()) as connection, connection:
        cursor = connection.cursor()
        for path in files:
            inserted, skipped = load_file(cursor, path)
            print(f"{path.name}: inserted={inserted}, skipped={skipped}")


if __name__ == "__main__":
    main()
