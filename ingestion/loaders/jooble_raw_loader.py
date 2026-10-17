import os
import json
from datetime import datetime
from pathlib import Path

import pyodbc
from dotenv import load_dotenv


# ============================================================
# PATHS / ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / ".env"
RAW_DATA_DIR = BASE_DIR / "data" / "raw"

load_dotenv(ENV_PATH)


# ============================================================
# SQL SERVER CONFIGURATION
# ============================================================

SERVER = os.getenv("MSSQL_HOST", "localhost")
PORT = os.getenv("MSSQL_PORT", "1433")
DATABASE = os.getenv("MSSQL_DATABASE", "JobMarketDWH")
USERNAME = os.getenv("MSSQL_USER", "sa")
PASSWORD = os.getenv("MSSQL_SA_PASSWORD")
DRIVER = os.getenv(
    "MSSQL_DRIVER",
    "ODBC Driver 17 for SQL Server"
)


def get_connection():

    connection_string = (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVER},{PORT};"
        f"DATABASE={DATABASE};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD};"
        f"TrustServerCertificate=yes;"
    )

    return pyodbc.connect(connection_string)


# ============================================================
# DATETIME PARSER
# ============================================================

def parse_iso_datetime(value):
    """
    Convert ISO timestamp to Python datetime.

    Python datetime supports max 6 fractional-second digits,
    while Jooble may return 7 digits.

    Examples:
        2026-10-16T23:45:53.660972
        2026-10-16T23:45:53.660972+00:00
        2026-10-07T19:20:50.5271635+00:00
        2026-10-16T23:45:53.660972Z
    """

    if not value:
        return None

    value = value.replace("Z", "+00:00")

    # Python 3.9 datetime supports microseconds
    # with a maximum precision of 6 digits.
    #
    # Jooble can return SQL Server-style 7-digit
    # fractional seconds, so truncate only the
    # fractional part before parsing.
    if "." in value:
        prefix, remainder = value.split(".", 1)

        timezone_position = None

        for index, char in enumerate(remainder):
            if char in ("+", "-"):
                timezone_position = index
                break

        if timezone_position is not None:
            fraction = remainder[:timezone_position]
            timezone_part = remainder[timezone_position:]
        else:
            fraction = remainder
            timezone_part = ""

        fraction = fraction[:6]

        value = (
            f"{prefix}."
            f"{fraction}"
            f"{timezone_part}"
        )

    return datetime.fromisoformat(value)


# ============================================================
# GET RAW FILES
# ============================================================

def get_raw_files():

    raw_files = sorted(
        RAW_DATA_DIR.glob("jooble_*.json"),
        key=lambda file: file.stat().st_mtime
    )

    if not raw_files:
        raise FileNotFoundError(
            "No Jooble RAW files found."
        )

    return raw_files


# ============================================================
# LOAD ONE RAW FILE
# ============================================================

def load_raw_file(cursor, json_file):

    with open(
        json_file,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    metadata = data.get(
        "metadata",
        {}
    )

    response_data = data.get(
        "response",
        {}
    )

    jobs = response_data.get(
        "jobs",
        []
    )

    source_system = metadata.get(
        "source_system",
        "Jooble"
    )

    source_platform = "Jooble"

    search_keyword = metadata.get(
        "search_keyword"
    )

    search_location = metadata.get(
        "search_location"
    )

    extracted_at = parse_iso_datetime(
        metadata.get("extracted_at")
    )

    raw_file_name = json_file.name

    inserted_count = 0
    updated_count = 0
    skipped_count = 0

    for job in jobs:

        source_job_id = job.get(
            "id"
        )

        if not source_job_id:
            skipped_count += 1
            continue

        description = job.get(
            "snippet"
        )

        source_updated_at = parse_iso_datetime(
            job.get("updated")
        )

        # ----------------------------------------------------
        # CHECK EXISTING OBSERVATION
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
            raw_file_name
        )

        existing_row = cursor.fetchone()

        # ----------------------------------------------------
        # EXISTING OBSERVATION -> ENRICH
        # ----------------------------------------------------

        if existing_row:

            cursor.execute(
                """
                UPDATE stg.JobPostingRaw
                SET
                    SourcePlatform = ?,
                    Description = ?,
                    SourceUpdatedAt = ?,
                    ExtractedAt = ?
                WHERE RawJobPostingID = ?
                """,
                source_platform,
                description,
                source_updated_at,
                extracted_at,
                existing_row.RawJobPostingID
            )

            updated_count += 1
            continue

        # ----------------------------------------------------
        # NEW OBSERVATION
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

            search_keyword,
            search_location,

            job.get("title"),
            job.get("location"),

            # Legacy Snippet + standardized Description.
            description,
            description,

            job.get("salary"),

            # Keep Jooble's original source field during
            # the migration period.
            job.get("source"),

            job.get("type"),

            # No reliable structured work-model field
            # in the current Jooble payload.
            None,

            job.get("link"),
            job.get("company"),

            # Jooble does not expose a reliable creation
            # timestamp in our current payload.
            None,

            # Jooble's updated field genuinely represents
            # the source-side update timestamp.
            source_updated_at,

            # Snapshot extraction timestamp from our collector.
            extracted_at,

            raw_file_name
        )

        inserted_count += 1

    return (
        len(jobs),
        inserted_count,
        updated_count,
        skipped_count
    )


# ============================================================
# BATCH LOAD
# ============================================================

def load_all_raw_files():

    raw_files = get_raw_files()

    connection = get_connection()
    cursor = connection.cursor()

    total_jobs = 0
    total_inserted = 0
    total_updated = 0
    total_skipped = 0

    print()
    print("=" * 70)
    print("JOOBLE RAW -> MSSQL LOADER")
    print("=" * 70)
    print(
        f"RAW files found : {len(raw_files)}"
    )
    print()

    try:

        for index, json_file in enumerate(
            raw_files,
            start=1
        ):

            (
                jobs_found,
                inserted,
                updated,
                skipped
            ) = load_raw_file(
                cursor,
                json_file
            )

            total_jobs += jobs_found
            total_inserted += inserted
            total_updated += updated
            total_skipped += skipped

            print(
                f"[{index}/{len(raw_files)}] "
                f"{json_file.name}"
            )

            print(
                f"    Jobs     : {jobs_found}"
            )

            print(
                f"    Inserted : {inserted}"
            )

            print(
                f"    Updated  : {updated}"
            )

            print(
                f"    Skipped  : {skipped}"
            )

        connection.commit()

        print()
        print("=" * 70)
        print("RAW BATCH LOAD COMPLETED")
        print("=" * 70)
        print(
            f"Jobs found : {total_jobs}"
        )
        print(
            f"Inserted   : {total_inserted}"
        )
        print(
            f"Updated    : {total_updated}"
        )
        print(
            f"Skipped    : {total_skipped}"
        )

    except Exception as error:

        connection.rollback()

        print()
        print(
            "RAW batch load failed."
        )
        print(
            "Transaction rolled back."
        )
        print(error)

        raise

    finally:

        cursor.close()
        connection.close()


if __name__ == "__main__":

    load_all_raw_files()