import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pyodbc
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

load_dotenv(PROJECT_ROOT / ".env")


def get_connection():
    driver = os.getenv(
        "MSSQL_DRIVER",
        "ODBC Driver 17 for SQL Server"
    )
    host = os.getenv(
        "MSSQL_HOST",
        "localhost"
    )
    port = os.getenv(
        "MSSQL_PORT",
        "1433"
    )
    database = os.getenv(
        "MSSQL_DATABASE",
        "JobMarketDWH"
    )
    user = os.getenv(
        "MSSQL_USER",
        "sa"
    )
    password = os.getenv(
        "MSSQL_SA_PASSWORD"
    )

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={host},{port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"TrustServerCertificate=yes;"
    )

    return pyodbc.connect(connection_string)


def unix_ms_to_datetime(value):
    """
    Lever createdAt is Unix time in milliseconds.
    Convert it to a UTC datetime.
    """
    if value is None:
        return None

    return datetime.fromtimestamp(
        value / 1000,
        tz=timezone.utc
    )


def parse_iso_datetime(value):
    """
    Convert RAW metadata ISO timestamp to datetime.

    Example:
        2026-10-17T10:33:39.052109+00:00
    """
    if not value:
        return None

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def build_full_text(job):
    """
    Build complete searchable text from Lever fields.

    Important qualification and responsibility information
    can live inside lists[].content, so descriptionPlain
    alone is not sufficient.
    """
    parts = []

    for field in [
        "openingPlain",
        "descriptionPlain",
        "descriptionBodyPlain",
        "additionalPlain"
    ]:
        value = job.get(field)

        if value:
            parts.append(value)

    for item in job.get("lists") or []:
        section_title = item.get("text")
        section_content = item.get("content")

        if section_title:
            parts.append(section_title)

        if section_content:
            parts.append(section_content)

    return "\n".join(parts)


def load_file(cursor, filepath):
    with open(
        filepath,
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    metadata = data.get(
        "metadata",
        {}
    )

    jobs = (
        data
        .get("response", {})
        .get("jobs", [])
    )

    source_system = metadata.get(
        "source_system",
        "Lever"
    )

    source_site = metadata.get(
        "source_site"
    )

    company_from_config = metadata.get(
        "company"
    )

    extracted_at = parse_iso_datetime(
        metadata.get("extracted_at")
    )

    raw_filename = filepath.name

    inserted = 0
    updated = 0
    skipped = 0

    for job in jobs:
        source_job_id = job.get(
            "id"
        )

        if not source_job_id:
            skipped += 1
            continue

        categories = (
            job.get("categories")
            or {}
        )

        job_title = job.get(
            "text"
        )

        job_location = categories.get(
            "location"
        )

        employment_type = categories.get(
            "commitment"
        )

        description = build_full_text(
            job
        )

        job_link = job.get(
            "hostedUrl"
        )

        # Lever createdAt represents creation/publication time.
        source_created_at = unix_ms_to_datetime(
            job.get("createdAt")
        )

        source_platform = "Lever"

        # Snapshot-level idempotency:
        # same advert may exist in multiple snapshots,
        # but one RAW file must represent only one observation.
        cursor.execute(
            """
            SELECT RawJobPostingID
            FROM stg.JobPostingRaw
            WHERE SourceSystem = ?
              AND SourceJobID = ?
              AND RawFileName = ?
            """,
            source_system,
            source_job_id,
            raw_filename
        )

        existing_row = cursor.fetchone()

        if existing_row:
            # Enrich existing historical observations with
            # standardized fields.
            cursor.execute(
                """
                UPDATE stg.JobPostingRaw
                SET
                    SourcePlatform = ?,
                    Description = ?,
                    SourceCreatedAt = ?,
                    ExtractedAt = ?
                WHERE RawJobPostingID = ?
                """,
                source_platform,
                description,
                source_created_at,
                extracted_at,
                existing_row.RawJobPostingID
            )

            updated += 1
            continue

        cursor.execute(
            """
            INSERT INTO stg.JobPostingRaw
            (
                SourceJobID,
                SourceSystem,
                SourcePlatform,

                SearchKeyword,
                SearchLocation,

                JobTitle,
                JobLocation,

                Snippet,
                Description,

                Salary,
                Source,

                EmploymentType,
                WorkModel,

                JobLink,
                Company,

                SourceCreatedAt,
                SourceUpdatedAt,
                ExtractedAt,

                RawFileName
            )
            VALUES
            (
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?,
                ?
            )
            """,
            source_job_id,
            source_system,
            source_platform,

            # Lever is a complete ATS listing,
            # not a keyword-search source.
            None,
            None,

            job_title,
            job_location,

            # Legacy column retained during migration.
            description,
            description,

            # Salary is not consistently available.
            None,

            # Legacy Source column retained during migration.
            source_site,

            employment_type,

            # No reliable dedicated work-model field
            # in the current Lever payload.
            None,

            job_link,
            company_from_config,

            source_created_at,

            # We do not currently have a reliable
            # source-updated timestamp from Lever.
            None,

            extracted_at,

            raw_filename
        )

        inserted += 1

    return inserted, updated, skipped


def main():
    files = sorted(
        RAW_DIR.glob(
            "lever_*.json"
        )
    )

    if not files:
        print(
            "No Lever RAW files found."
        )
        return

    print("=" * 60)
    print("LEVER RAW -> SQL LOADER")
    print("=" * 60)

    connection = get_connection()

    total_inserted = 0
    total_updated = 0
    total_skipped = 0

    try:
        cursor = connection.cursor()

        for filepath in files:
            inserted, updated, skipped = load_file(
                cursor,
                filepath
            )

            print(
                f"{filepath.name}: "
                f"inserted={inserted}, "
                f"updated={updated}, "
                f"skipped={skipped}"
            )

            total_inserted += inserted
            total_updated += updated
            total_skipped += skipped

        connection.commit()

        print("\n" + "=" * 60)
        print("LOAD COMPLETED")
        print(
            f"Inserted : {total_inserted}"
        )
        print(
            f"Updated  : {total_updated}"
        )
        print(
            f"Skipped  : {total_skipped}"
        )
        print("=" * 60)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()