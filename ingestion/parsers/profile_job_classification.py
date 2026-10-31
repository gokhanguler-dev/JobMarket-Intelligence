import os
from pathlib import Path

import pyodbc
from config.env_loader import load_project_env

from ingestion.parsers.job_classifier import classify_job


# ============================================================
# PATHS / ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

load_project_env(BASE_DIR)


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


def profile_classification():

    connection = get_connection()
    cursor = connection.cursor()

    query = """
        SELECT
            JobPostingStgID,
            JobTitle,
            Company
        FROM stg.JobPosting
        ORDER BY JobPostingStgID;
    """

    cursor.execute(query)
    jobs = cursor.fetchall()

    print()
    print("=" * 100)
    print("JOB ROLE / SENIORITY PROFILING")
    print("=" * 100)
    print(f"Jobs : {len(jobs)}")
    print()

    role_counts = {}
    seniority_counts = {}

    for job in jobs:

        classification = classify_job(job.JobTitle)

        normalized_role = classification["normalized_role"]
        seniority = classification["seniority"]

        role_counts[normalized_role] = (
            role_counts.get(normalized_role, 0) + 1
        )

        seniority_counts[seniority] = (
            seniority_counts.get(seniority, 0) + 1
        )

        print("-" * 100)
        print(f"ID        : {job.JobPostingStgID}")
        print(f"Title     : {job.JobTitle}")
        print(f"Company   : {job.Company}")
        print(f"Role      : {normalized_role}")
        print(f"Seniority : {seniority}")

    print()
    print("=" * 100)
    print("ROLE SUMMARY")
    print("=" * 100)

    for role, count in sorted(
        role_counts.items(),
        key=lambda item: (-item[1], item[0])
    ):
        print(f"{role:<30} {count}")

    print()
    print("=" * 100)
    print("SENIORITY SUMMARY")
    print("=" * 100)

    for seniority, count in sorted(
        seniority_counts.items(),
        key=lambda item: (-item[1], item[0])
    ):
        print(f"{seniority:<30} {count}")

    cursor.close()
    connection.close()


if __name__ == "__main__":
    profile_classification()