import os
from pathlib import Path

import pyodbc
from dotenv import load_dotenv

from ingestion.parsers.job_classifier import classify_job


# ============================================================
# PATHS / ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / ".env"

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
# RECLASSIFICATION
# ============================================================

def reclassify_jobs():

    connection = get_connection()
    cursor = connection.cursor()

    select_sql = """
        SELECT
            JobPostingStgID,
            JobTitle,
            NormalizedRole,
            Seniority
        FROM stg.JobPosting
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
    print("=" * 70)
    print("JOB RECLASSIFICATION")
    print("=" * 70)
    print(f"Jobs found : {len(jobs)}")
    print()

    changed_count = 0
    unchanged_count = 0

    try:

        for job in jobs:

            classification = classify_job(
                job.JobTitle
            )

            new_role = (
                classification["normalized_role"]
            )

            new_seniority = (
                classification["seniority"]
            )

            old_role = job.NormalizedRole
            old_seniority = job.Seniority

            # Only issue UPDATE when classification changed.
            if (
                old_role != new_role
                or old_seniority != new_seniority
            ):

                cursor.execute(
                    update_sql,
                    new_role,
                    new_seniority,
                    job.JobPostingStgID
                )

                changed_count += 1

                print(
                    f"[CHANGED] {job.JobTitle}"
                )

                print(
                    f"    Role      : "
                    f"{old_role} -> {new_role}"
                )

                print(
                    f"    Seniority : "
                    f"{old_seniority} -> {new_seniority}"
                )

            else:

                unchanged_count += 1

        connection.commit()

        print()
        print("=" * 70)
        print("RECLASSIFICATION COMPLETED")
        print("=" * 70)
        print(f"Jobs checked : {len(jobs)}")
        print(f"Changed      : {changed_count}")
        print(f"Unchanged    : {unchanged_count}")

    except Exception as error:

        connection.rollback()

        print()
        print("=" * 70)
        print("RECLASSIFICATION FAILED")
        print("=" * 70)
        print("Transaction rolled back.")
        print(error)

        raise

    finally:

        cursor.close()
        connection.close()


if __name__ == "__main__":

    reclassify_jobs()