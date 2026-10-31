import html
import json
import os
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

import pyodbc
from config.env_loader import load_project_env


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

load_project_env(PROJECT_ROOT)


# ============================================================
# DATABASE
# ============================================================

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


# ============================================================
# DATETIME
# ============================================================

def parse_iso_datetime(value):
    """
    Convert ISO timestamp values returned by Greenhouse
    into Python datetime objects.

    Examples:
        2026-10-16T08:00:59-04:00
        2026-10-22T18:46:16.491705+00:00
        2026-10-22T18:46:16Z
    """
    if not value:
        return None

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


# ============================================================
# HTML CLEANING
# ============================================================

class HTMLTextExtractor(HTMLParser):
    """
    Small standard-library HTML parser used to extract
    readable text from Greenhouse job descriptions.
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
        if data:
            self.parts.append(data)

    def get_text(self):
        return "".join(self.parts)


def clean_html_text(value):
    """
    Greenhouse content can contain HTML that is itself
    HTML-entity encoded, for example:

        &lt;p&gt;Build scalable systems&lt;/p&gt;

    First decode entities, then remove HTML tags and
    normalize whitespace.
    """
    if not value:
        return None

    decoded = html.unescape(value)

    parser = HTMLTextExtractor()
    parser.feed(decoded)

    text = parser.get_text()

    lines = []

    for line in text.splitlines():
        cleaned_line = " ".join(line.split())

        if cleaned_line:
            lines.append(cleaned_line)

    if not lines:
        return None

    return "\n".join(lines)


# ============================================================
# RAW FILE LOADER
# ============================================================

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
        "Greenhouse"
    )

    source_board = metadata.get(
        "source_board"
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

        # ----------------------------------------------------
        # SOURCE JOB ID
        # ----------------------------------------------------

        source_job_id = job.get("id")

        if source_job_id is None:
            skipped += 1
            continue

        source_job_id = str(source_job_id)

        # ----------------------------------------------------
        # STANDARDIZED FIELDS
        # ----------------------------------------------------

        job_title = job.get(
            "title"
        )

        location = (
            job.get("location")
            or {}
        )

        job_location = location.get(
            "name"
        )

        description = clean_html_text(
            job.get("content")
        )

        job_link = job.get(
            "absolute_url"
        )

        company = (
            company_from_config
            or job.get("company_name")
        )

        source_created_at = parse_iso_datetime(
            job.get("first_published")
        )

        source_updated_at = parse_iso_datetime(
            job.get("updated_at")
        )

        source_platform = "Greenhouse"

        # ----------------------------------------------------
        # SNAPSHOT IDEMPOTENCY
        # ----------------------------------------------------
        #
        # Same job may appear in multiple daily snapshots.
        #
        # Each RAW file represents one observation.
        # Therefore:
        #
        # SourceSystem + SourceJobID + RawFileName
        #
        # uniquely identifies one RAW observation.
        # ----------------------------------------------------

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

            # Existing snapshot:
            # enrich/update standardized fields rather than
            # inserting a duplicate observation.

            cursor.execute(
                """
                UPDATE stg.JobPostingRaw
                SET
                    SourcePlatform = ?,
                    JobTitle = ?,
                    JobLocation = ?,
                    Snippet = ?,
                    Description = ?,
                    Source = ?,
                    JobLink = ?,
                    Company = ?,
                    SourceCreatedAt = ?,
                    SourceUpdatedAt = ?,
                    ExtractedAt = ?
                WHERE RawJobPostingID = ?
                """,
                source_platform,
                job_title,
                job_location,
                description,
                description,
                source_board,
                job_link,
                company,
                source_created_at,
                source_updated_at,
                extracted_at,
                existing_row.RawJobPostingID
            )

            updated += 1
            continue

        # ----------------------------------------------------
        # INSERT NEW RAW OBSERVATION
        # ----------------------------------------------------

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

            # Greenhouse board is a complete ATS listing,
            # not a keyword-search result.
            None,
            None,

            job_title,
            job_location,

            # Legacy Snippet column retained during migration.
            description,
            description,

            # Salary is not consistently exposed by
            # Greenhouse public job-board payloads.
            None,

            # Legacy Source column:
            # retain the Greenhouse board identifier.
            source_board,

            # No reliable standardized fields currently
            # available for these attributes.
            None,
            None,

            job_link,
            company,

            source_created_at,
            source_updated_at,
            extracted_at,

            raw_filename
        )

        inserted += 1

    return inserted, updated, skipped


# ============================================================
# MAIN
# ============================================================

def main():
    files = sorted(
        RAW_DIR.glob(
            "greenhouse_*.json"
        )
    )

    if not files:
        print(
            "No Greenhouse RAW files found."
        )
        return

    print("=" * 60)
    print("GREENHOUSE RAW -> SQL LOADER")
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