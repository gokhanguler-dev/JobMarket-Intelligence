import os
from pathlib import Path

import pyodbc
from dotenv import load_dotenv

from ingestion.parsers.job_classifier import classify_job


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)


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


def backfill_classification():

    connection = get_connection()
    cursor = connection.cursor()

    select_sql = """
        SELECT
            JobPostingStgID,
            JobTitle
        FROM stg.JobPosting
        WHERE NormalizedRole IS NULL
           OR Seniority IS NULL
        ORDER BY JobPostingStgID;
    """

    update_sql = """
        UPDATE stg.JobPosting
        SET
            NormalizedRole = ?,
            Seniority = ?
        WHERE JobPostingStgID = ?;
    """

    cursor.execute(select_sql)
    jobs = cursor.fetchall()

    print()
    print("=" * 60)
    print("JOB CLASSIFICATION BACKFILL")
    print("=" * 60)
    print(f"Jobs to classify : {len(jobs)}")
    print()

    updated_count = 0

    try:

        for job in jobs:

            classification = classify_job(
                job.JobTitle
            )

            normalized_role = (
                classification["normalized_role"]
            )

            seniority = (
                classification["seniority"]
            )

            cursor.execute(
                update_sql,
                normalized_role,
                seniority,
                job.JobPostingStgID
            )

            updated_count += 1

            print(
                f"[{updated_count}/{len(jobs)}] "
                f"{job.JobTitle} "
                f"-> {normalized_role} / {seniority}"
            )

        connection.commit()

        print()
        print("=" * 60)
        print("BACKFILL COMPLETED")
        print("=" * 60)
        print(f"Jobs updated : {updated_count}")

    except Exception as error:

        connection.rollback()

        print()
        print("Backfill failed.")
        print("Transaction rolled back.")
        print(error)

        raise

    finally:

        cursor.close()
        connection.close()


if __name__ == "__main__":
    backfill_classification()