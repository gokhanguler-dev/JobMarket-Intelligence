import json
import os
import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

import pyodbc
from config.env_loader import load_project_env


# ---------------------------------------------------------
# PATHS / ENV
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw"

load_project_env(BASE_DIR)


# ---------------------------------------------------------
# HTML CLEANER
# ---------------------------------------------------------

class HTMLTextExtractor(HTMLParser):
    """
    Lightweight HTML -> text converter.

    Keeps the loader dependency-free apart from the existing
    project packages and preserves readable spacing between
    paragraphs/list items.
    """

    BLOCK_TAGS = {
        "p",
        "div",
        "br",
        "li",
        "ul",
        "ol",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "section",
        "article",
    }

    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)

    def get_text(self):
        text = unescape("".join(self.parts))

        text = text.replace("\xa0", " ")

        text = re.sub(
            r"[ \t]+",
            " ",
            text,
        )

        text = re.sub(
            r" *\n *",
            "\n",
            text,
        )

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text,
        )

        return text.strip()


def clean_html_text(value):
    if not value:
        return None

    parser = HTMLTextExtractor()
    parser.feed(value)

    text = parser.get_text()

    return text if text else None


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

def get_connection():
    driver = os.getenv(
        "MSSQL_DRIVER",
        "ODBC Driver 17 for SQL Server",
    )

    host = os.getenv(
        "MSSQL_HOST",
        "localhost",
    )

    port = os.getenv(
        "MSSQL_PORT",
        "1433",
    )

    database = os.getenv(
        "MSSQL_DATABASE",
        "JobMarketDWH",
    )

    user = os.getenv(
        "MSSQL_USER",
        "sa",
    )

    password = os.getenv("MSSQL_SA_PASSWORD")

    if not password:
        raise RuntimeError(
            "MSSQL_SA_PASSWORD is not configured."
        )

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


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def get_source_job_id(summary, detail):
    """
    Prefer the human-readable Workday requisition ID.

    Fallback order:
        jobReqId
        jobPostingId
        internal Workday id
        externalPath
    """

    return str(
        detail.get("jobReqId")
        or detail.get("jobPostingId")
        or detail.get("id")
        or summary.get("externalPath")
    )


def get_job_link(metadata, summary, detail):
    external_url = detail.get("externalUrl")

    if external_url:
        return external_url

    host = metadata.get("host")
    site = metadata.get("site")
    external_path = summary.get("externalPath")

    if host and site and external_path:
        return (
            f"https://{host}"
            f"/{site}"
            f"{external_path}"
        )

    return None


# ---------------------------------------------------------
# LOAD ONE RAW FILE
# ---------------------------------------------------------

def load_file(cursor, raw_file):
    with open(
        raw_file,
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    metadata = payload.get(
        "metadata",
        {},
    )

    jobs = payload.get(
        "jobs",
        [],
    )

    source_system = metadata.get(
        "source_system",
        "Workday",
    )

    source_platform = metadata.get(
        "source_platform",
        "Workday",
    )

    company = metadata.get("company")
    extracted_at = metadata.get("extracted_at")

    inserted = 0
    updated = 0
    skipped = 0

    for item in jobs:
        summary = item.get(
            "summary",
            {},
        )

        detail = item.get(
            "jobPostingInfo",
            {},
        )

        source_job_id = get_source_job_id(
            summary,
            detail,
        )

        if not source_job_id:
            skipped += 1
            continue

        job_title = (
            detail.get("title")
            or summary.get("title")
        )

        job_location = (
            detail.get("location")
            or summary.get("locationsText")
            or metadata.get("location_name")
        )

        description = clean_html_text(
            detail.get("jobDescription")
        )

        employment_type = (
            detail.get("timeType")
            or summary.get("timeType")
        )

        job_link = get_job_link(
            metadata,
            summary,
            detail,
        )

        source_created_at = (
            detail.get("startDate")
            or detail.get("posted")
        )

        source_updated_at = None

        # Legacy Source column:
        # keep the Workday site identifier for lineage.
        source = metadata.get("site")

        # -------------------------------------------------
        # SNAPSHOT IDEMPOTENCY
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM stg.JobPostingRaw
            WHERE SourceSystem = ?
              AND SourceJobID = ?
              AND RawFileName = ?
            """,
            source_system,
            source_job_id,
            raw_file.name,
        )

        exists = cursor.fetchone()[0]

        if exists:
            # Enrich/re-align the existing snapshot row.
            cursor.execute(
                """
                UPDATE stg.JobPostingRaw
                SET
                    SourcePlatform = ?,
                    JobTitle = ?,
                    JobLocation = ?,
                    Description = ?,
                    EmploymentType = ?,
                    JobLink = ?,
                    Company = ?,
                    SourceCreatedAt = ?,
                    SourceUpdatedAt = ?,
                    ExtractedAt = ?
                WHERE SourceSystem = ?
                  AND SourceJobID = ?
                  AND RawFileName = ?
                """,
                source_platform,
                job_title,
                job_location,
                description,
                employment_type,
                job_link,
                company,
                source_created_at,
                source_updated_at,
                extracted_at,
                source_system,
                source_job_id,
                raw_file.name,
            )

            updated += 1
            continue

        # -------------------------------------------------
        # INSERT
        # -------------------------------------------------

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
            source_job_id,
            source_system,
            source_platform,
            None,                    # SearchKeyword
            None,                    # SearchLocation
            job_title,
            job_location,
            description,             # Snippet
            description,             # Description
            None,                    # Salary
            source,
            employment_type,
            None,                    # WorkModel
            job_link,
            company,
            source_created_at,
            source_updated_at,
            extracted_at,
            raw_file.name,
        )

        inserted += 1

    return inserted, updated, skipped


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():
    raw_files = sorted(
        RAW_DIR.glob("workday_*.json")
    )

    print(
        f"[INFO] Workday raw files found: "
        f"{len(raw_files)}"
    )

    if not raw_files:
        print(
            "[WARN] No Workday raw files found."
        )
        return

    connection = get_connection()
    cursor = connection.cursor()

    total_inserted = 0
    total_updated = 0
    total_skipped = 0

    try:
        for raw_file in raw_files:
            print(
                f"[LOAD] {raw_file.name}"
            )

            inserted, updated, skipped = load_file(
                cursor,
                raw_file,
            )

            total_inserted += inserted
            total_updated += updated
            total_skipped += skipped

            print(
                f"       inserted={inserted} "
                f"updated={updated} "
                f"skipped={skipped}"
            )

        connection.commit()

        print()
        print("=" * 70)
        print("[SUMMARY]")
        print(
            f"Inserted: {total_inserted}"
        )
        print(
            f"Updated: {total_updated}"
        )
        print(
            f"Skipped: {total_skipped}"
        )
        print("=" * 70)

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()