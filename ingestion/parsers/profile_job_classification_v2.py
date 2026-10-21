import os
from collections import Counter, defaultdict

import pyodbc
from dotenv import load_dotenv

from ingestion.parsers.job_classifier import classify_job


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv(override=True)

SQL_HOST = os.getenv("MSSQL_HOST", "localhost")
SQL_PORT = os.getenv("MSSQL_PORT", "1433")
SQL_DATABASE = os.getenv("MSSQL_DATABASE", "JobMarketDWH")
SQL_USER = os.getenv("MSSQL_USER", "sa")
SQL_PASSWORD = os.getenv("MSSQL_SA_PASSWORD")


# ============================================================
# DATABASE CONNECTION
# ============================================================

connection_string = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={SQL_HOST},{SQL_PORT};"
    f"DATABASE={SQL_DATABASE};"
    f"UID={SQL_USER};"
    f"PWD={SQL_PASSWORD};"
    "TrustServerCertificate=yes;"
)


def get_jobs():
    connection = pyodbc.connect(connection_string)

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            JobPostingKey,
            JobTitle
        FROM dwh.FactJobPosting
        ORDER BY JobPostingKey;
        """
    )

    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    return rows


# ============================================================
# PROFILE
# ============================================================

def main():

    jobs = get_jobs()

    tech_status_counter = Counter()
    career_area_counter = Counter()
    role_counter = Counter()
    seniority_counter = Counter()

    unknown_titles = Counter()

    career_area_roles = defaultdict(Counter)

    classified_jobs = []

    for row in jobs:

        job_posting_key = row.JobPostingKey
        job_title = row.JobTitle

        classification = classify_job(job_title)

        tech_status = classification["is_tech_role"]
        career_area = classification["career_area"]
        normalized_role = classification["normalized_role"]
        seniority = classification["seniority"]
        matched_alias = classification["matched_role_alias"]

        tech_status_counter[tech_status] += 1
        seniority_counter[seniority] += 1

        if tech_status == "Tech":

            career_area_counter[career_area] += 1
            role_counter[normalized_role] += 1

            career_area_roles[career_area][normalized_role] += 1

        else:

            unknown_titles[job_title] += 1

        classified_jobs.append(
            {
                "job_posting_key": job_posting_key,
                "job_title": job_title,
                "tech_status": tech_status,
                "career_area": career_area,
                "normalized_role": normalized_role,
                "seniority": seniority,
                "matched_alias": matched_alias
            }
        )

    total_jobs = len(jobs)

    tech_jobs = tech_status_counter["Tech"]
    unknown_jobs = tech_status_counter["Unknown"]

    tech_pct = (
        tech_jobs / total_jobs * 100
        if total_jobs
        else 0
    )

    unknown_pct = (
        unknown_jobs / total_jobs * 100
        if total_jobs
        else 0
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print("JOB CLASSIFICATION V2 - DRY RUN")
    print("=" * 70)

    print()
    print(f"Total jobs     : {total_jobs}")
    print(f"Tech jobs      : {tech_jobs} ({tech_pct:.2f}%)")
    print(f"Unknown jobs   : {unknown_jobs} ({unknown_pct:.2f}%)")

    # ========================================================
    # CAREER AREAS
    # ========================================================

    print()
    print("=" * 70)
    print("CAREER AREA DISTRIBUTION")
    print("=" * 70)

    for career_area, count in career_area_counter.most_common():

        pct = (
            count / tech_jobs * 100
            if tech_jobs
            else 0
        )

        print(
            f"{career_area:<35} "
            f"{count:>5} "
            f"({pct:>6.2f}%)"
        )

    # ========================================================
    # ROLES
    # ========================================================

    print()
    print("=" * 70)
    print("ROLE DISTRIBUTION")
    print("=" * 70)

    for role, count in role_counter.most_common():

        print(
            f"{role:<35} "
            f"{count:>5}"
        )

    # ========================================================
    # CAREER AREA -> ROLE
    # ========================================================

    print()
    print("=" * 70)
    print("CAREER AREA -> ROLE")
    print("=" * 70)

    for career_area in sorted(career_area_roles):

        print()
        print(f"[{career_area}]")

        for role, count in career_area_roles[
            career_area
        ].most_common():

            print(
                f"  {role:<32} "
                f"{count:>5}"
            )

    # ========================================================
    # SENIORITY
    # ========================================================

    print()
    print("=" * 70)
    print("SENIORITY DISTRIBUTION - ALL JOBS")
    print("=" * 70)

    for seniority, count in seniority_counter.most_common():

        pct = (
            count / total_jobs * 100
            if total_jobs
            else 0
        )

        print(
            f"{seniority:<20} "
            f"{count:>5} "
            f"({pct:>6.2f}%)"
        )

    # ========================================================
    # UNKNOWN TITLES
    # ========================================================

    print()
    print("=" * 70)
    print("UNKNOWN TITLES")
    print("=" * 70)

    print(
        f"Distinct unknown titles: "
        f"{len(unknown_titles)}"
    )

    print()

    for title, count in unknown_titles.most_common():

        print(
            f"{count:>3} | {title}"
        )

    print()
    print("=" * 70)
    print("DRY RUN COMPLETED - DATABASE NOT MODIFIED")
    print("=" * 70)


if __name__ == "__main__":
    main()