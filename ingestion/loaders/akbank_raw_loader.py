import html
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import pyodbc
from bs4 import BeautifulSoup
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
    Convert Unix milliseconds to UTC datetime.
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
        2026-10-17T11:35:29.379123+00:00
    """
    if not value:
        return None

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def clean_html_text(value):
    """
    Convert Akbank HTML content into clean searchable text.
    """
    if not value:
        return ""

    value = html.unescape(value)

    soup = BeautifulSoup(
        value,
        "html.parser"
    )

    text = soup.get_text(
        " ",
        strip=True
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def build_full_text(detail):
    """
    Build the standardized job description used by
    downstream role and skill processing.
    """
    parts = []

    description_header = detail.get(
        "jobDescriptionHeader"
    )

    description = clean_html_text(
        detail.get("jobDescription")
    )

    qualifications_header = detail.get(
        "jobQualificationsHeader"
    )

    qualifications = clean_html_text(
        detail.get("jobQualifications")
    )

    if description_header:
        parts.append(description_header)

    if description:
        parts.append(description)

    if qualifications_header:
        parts.append(qualifications_header)

    if qualifications:
        parts.append(qualifications)

    extra_header = detail.get(
        "jobSoIsThatAllExplanationHeader"
    )

    extra_text = clean_html_text(
        detail.get("jobSoIsThatAllExplanation")
    )

    if extra_header:
        parts.append(extra_header)

    if extra_text:
        parts.append(extra_text)

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
        "Akbank"
    )

    company_from_metadata = metadata.get(
        "company",
        "Akbank"
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
            "source_job_id"
        )

        if not source_job_id:
            skipped += 1
            continue

        list_data = job.get(
            "list"
        ) or {}

        detail = job.get(
            "detail"
        ) or {}

        job_title = (
            detail.get("title")
            or list_data.get("title")
        )

        job_location = (
            detail.get("city")
            or list_data.get("city")
        )

        employment_type = (
            detail.get("workType")
            or list_data.get("workType")
        )

        work_model = (
            detail.get("workModel")
            or list_data.get("workModel")
        )

        job_link = job.get(
            "job_url"
        )

        description = build_full_text(
            detail
        )

        # Keep useful structured metadata inside searchable
        # description as well as in dedicated columns.
        metadata_text_parts = []

        if work_model:
            metadata_text_parts.append(
                f"Çalışma Modeli: {work_model}"
            )

        experience = (
            detail.get("experience")
            or list_data.get("experience")
        )

        if experience:
            metadata_text_parts.append(
                f"Deneyim: {experience}"
            )

        if metadata_text_parts:
            description = "\n".join(
                metadata_text_parts
                + ([description] if description else [])
            )

        # Akbank createDate represents advert creation time.
        source_created_at = unix_ms_to_datetime(
            detail.get("createDate")
            or list_data.get("createDate")
        )

        source_platform = "Akbank Career"

        # Snapshot-level idempotency.
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
            # Existing historical rows are enriched with
            # the newly standardized fields.
            cursor.execute(
                """
                UPDATE stg.JobPostingRaw
                SET
                    SourcePlatform = ?,
                    Description = ?,
                    WorkModel = ?,
                    SourceCreatedAt = ?,
                    ExtractedAt = ?
                WHERE RawJobPostingID = ?
                """,
                source_platform,
                description,
                work_model,
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

            None,
            None,

            job_title,
            job_location,

            # Keep legacy Snippet populated during migration.
            description,
            description,

            None,

            # Legacy Source column retained temporarily.
            source_platform,

            employment_type,
            work_model,

            job_link,
            company_from_metadata,

            source_created_at,

            # Akbank API currently gives us createDate,
            # not a reliable last-updated timestamp.
            None,

            extracted_at,

            raw_filename
        )

        inserted += 1

    return inserted, updated, skipped


def main():
    files = sorted(
        RAW_DIR.glob(
            "akbank_*.json"
        )
    )

    if not files:
        print(
            "No Akbank RAW files found."
        )
        return

    print("=" * 60)
    print("AKBANK RAW -> SQL LOADER")
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