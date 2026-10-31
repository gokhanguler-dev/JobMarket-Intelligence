import json
import os
import re
from html.parser import HTMLParser
from pathlib import Path

import pyodbc
from config.env_loader import load_project_env


BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw"

load_project_env(BASE_DIR)


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.parts.append(text)

    def get_text(self):
        return " ".join(self.parts)


def clean_html(value):
    if not value:
        return None

    parser = HTMLTextExtractor()
    parser.feed(str(value))

    text = parser.get_text()
    text = re.sub(r"\s+", " ", text).strip()

    return text or None


def get_connection():
    host = os.getenv("MSSQL_HOST", "localhost")
    port = os.getenv("MSSQL_PORT", "1433")
    database = os.getenv("MSSQL_DATABASE", "JobMarketDWH")
    user = os.getenv("MSSQL_USER", "sa")
    password = os.getenv("MSSQL_SA_PASSWORD")
    driver = os.getenv(
        "MSSQL_DRIVER",
        "ODBC Driver 17 for SQL Server",
    )

    if not password:
        raise ValueError("MSSQL_SA_PASSWORD is not defined.")

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={host},{port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"TrustServerCertificate=yes;"
    )

    return pyodbc.connect(
        connection_string,
        autocommit=False,
    )


def get_section_text(detail, section_name):
    sections = (
        detail
        .get("jobAd", {})
        .get("sections", {})
    )

    section = sections.get(section_name)

    if not section:
        return None

    if isinstance(section, dict):
        return clean_html(section.get("text"))

    return clean_html(section)


def build_description(detail):
    """
    Deliberately excludes companyDescription.

    Company boilerplate can pollute downstream
    skill/capability extraction.
    """

    preferred_sections = [
        "jobDescription",
        "qualifications",
        "additionalInformation",
    ]

    parts = []

    for section_name in preferred_sections:
        text = get_section_text(detail, section_name)

        if text and text not in parts:
            parts.append(text)

    if not parts:
        # Defensive fallback:
        # collect non-company sections if SmartRecruiters uses
        # a slightly different section name for a company.
        sections = (
            detail
            .get("jobAd", {})
            .get("sections", {})
        )

        for section_name, section in sections.items():
            if section_name == "companyDescription":
                continue

            if isinstance(section, dict):
                text = clean_html(section.get("text"))
            else:
                text = clean_html(section)

            if text and text not in parts:
                parts.append(text)

    description = "\n\n".join(parts).strip()

    return description or None


def build_location(detail, summary):
    location = detail.get("location") or summary.get("location") or {}

    full_location = location.get("fullLocation")

    if full_location:
        return full_location

    values = [
        location.get("city"),
        location.get("region"),
        location.get("country"),
    ]

    values = [
        str(value).strip()
        for value in values
        if value
    ]

    return ", ".join(values) or None


def get_employment_type(detail, summary):
    employment = (
        detail.get("typeOfEmployment")
        or summary.get("typeOfEmployment")
        or {}
    )

    if isinstance(employment, dict):
        return (
            employment.get("label")
            or employment.get("id")
        )

    return str(employment) if employment else None


def get_work_model(detail, summary):
    location = detail.get("location") or summary.get("location") or {}

    if location.get("remote") is True:
        return "Remote"

    if location.get("hybrid") is True:
        return "Hybrid"

    if (
        location.get("remote") is False
        and location.get("hybrid") is False
    ):
        return "On-site"

    return None


def load_file(cursor, file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    metadata = payload.get("metadata", {})
    response = payload.get("response", {})

    jobs = response.get("jobs", [])

    source_system = metadata.get(
        "source_system",
        "SmartRecruiters",
    )

    source_platform = metadata.get(
        "source_platform",
        "SmartRecruiters",
    )

    metadata_company = metadata.get("company")
    company_identifier = metadata.get("company_identifier")
    extracted_at = metadata.get("extracted_at")

    inserted = 0
    updated = 0
    skipped = 0

    for item in jobs:
        summary = item.get("summary") or {}
        detail = item.get("detail") or {}

        source_job_id = (
            detail.get("id")
            or summary.get("id")
            or detail.get("uuid")
            or summary.get("uuid")
        )

        if not source_job_id:
            skipped += 1
            continue

        company_data = (
            detail.get("company")
            or summary.get("company")
            or {}
        )

        company = (
            company_data.get("name")
            or metadata_company
        )

        job_title = (
            detail.get("name")
            or summary.get("name")
        )

        job_location = build_location(
            detail,
            summary,
        )

        description = build_description(detail)

        employment_type = get_employment_type(
            detail,
            summary,
        )

        work_model = get_work_model(
            detail,
            summary,
        )

        job_link = (
            detail.get("postingUrl")
            or summary.get("postingUrl")
        )

        source_created_at = (
            detail.get("releasedDate")
            or summary.get("releasedDate")
        )

        # SmartRecruiters payload currently gives us
        # publication date but no reliable updated timestamp.
        source_updated_at = None

        # Keep legacy Source populated consistently with
        # the source-specific identifier.
        source = company_identifier

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM stg.JobPostingRaw
            WHERE SourceSystem = ?
              AND SourceJobID = ?
              AND RawFileName = ?
            """,
            (
                source_system,
                str(source_job_id),
                file_path.name,
            ),
        )

        exists = cursor.fetchone()[0]

        if exists:
            cursor.execute(
                """
                UPDATE stg.JobPostingRaw
                SET
                    SourcePlatform = ?,
                    JobTitle = ?,
                    JobLocation = ?,
                    Description = ?,
                    EmploymentType = ?,
                    WorkModel = ?,
                    JobLink = ?,
                    Company = ?,
                    SourceCreatedAt = ?,
                    SourceUpdatedAt = ?,
                    ExtractedAt = ?,
                    Source = ?
                WHERE SourceSystem = ?
                  AND SourceJobID = ?
                  AND RawFileName = ?
                """,
                (
                    source_platform,
                    job_title,
                    job_location,
                    description,
                    employment_type,
                    work_model,
                    job_link,
                    company,
                    source_created_at,
                    source_updated_at,
                    extracted_at,
                    source,
                    source_system,
                    str(source_job_id),
                    file_path.name,
                ),
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
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?
            )
            """,
            (
                str(source_job_id),
                source_system,
                source_platform,
                None,  # SearchKeyword
                None,  # SearchLocation
                job_title,
                job_location,
                None,  # Snippet
                description,
                None,  # Salary
                source,
                employment_type,
                work_model,
                job_link,
                company,
                source_created_at,
                source_updated_at,
                extracted_at,
                file_path.name,
            ),
        )

        inserted += 1

    return inserted, updated, skipped


def main():
    raw_files = sorted(
        RAW_DIR.glob("smartrecruiters_*.json")
    )

    if not raw_files:
        print("[INFO] No SmartRecruiters raw files found.")
        return

    print("=" * 70)
    print("[START] SmartRecruiters RAW Loader")
    print(f"Raw files found: {len(raw_files)}")
    print("=" * 70)

    connection = get_connection()
    cursor = connection.cursor()

    total_inserted = 0
    total_updated = 0
    total_skipped = 0

    try:
        for file_path in raw_files:
            print()
            print(f"[FILE] {file_path.name}")

            inserted, updated, skipped = load_file(
                cursor,
                file_path,
            )

            total_inserted += inserted
            total_updated += updated
            total_skipped += skipped

            print(f"Inserted : {inserted}")
            print(f"Updated  : {updated}")
            print(f"Skipped  : {skipped}")

        connection.commit()

        print()
        print("=" * 70)
        print("[SUMMARY]")
        print(f"Inserted : {total_inserted}")
        print(f"Updated  : {total_updated}")
        print(f"Skipped  : {total_skipped}")
        print("[OK] Database changes committed.")
        print("=" * 70)

    except Exception:
        connection.rollback()
        print()
        print("[ERROR] Transaction rolled back.")
        raise

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()