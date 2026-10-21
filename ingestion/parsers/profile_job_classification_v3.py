import os
from collections import Counter, defaultdict

import pyodbc
from dotenv import load_dotenv

from ingestion.parsers.job_classifier import classify_job


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv(override=True)


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    connection_string = (
        f"DRIVER={{{os.getenv('MSSQL_DRIVER', 'ODBC Driver 17 for SQL Server')}}};"
        f"SERVER={os.getenv('MSSQL_HOST', 'localhost')},"
        f"{os.getenv('MSSQL_PORT', '1433')};"
        f"DATABASE={os.getenv('MSSQL_DATABASE', 'JobMarketDWH')};"
        f"UID={os.getenv('MSSQL_USER', 'sa')};"
        f"PWD={os.getenv('MSSQL_SA_PASSWORD')};"
        "TrustServerCertificate=yes;"
    )

    return pyodbc.connect(connection_string)


# ============================================================
# DATA RETRIEVAL
# ============================================================

def get_jobs():
    """
    Canonical job postings are read from dwh.FactJobPosting.

    Description is not stored in FactJobPosting, therefore the latest
    matching standardized STG record is retrieved by:

        SourceSystem + SourceJobID

    This keeps the classifier working against the canonical DWH job
    universe while still allowing description-based analysis.
    """

    query = """
        SELECT
            f.JobPostingKey,
            f.SourceSystem,
            f.SourceJobID,
            f.JobTitle,
            s.Description

        FROM dwh.FactJobPosting f

        OUTER APPLY
        (
            SELECT TOP 1
                j.Description
            FROM stg.JobPosting j
            WHERE j.SourceSystem = f.SourceSystem
              AND j.SourceJobID = f.SourceJobID
            ORDER BY
                j.ExtractedAt DESC
        ) s

        ORDER BY
            f.JobPostingKey;
    """

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(query)

        return cursor.fetchall()


# ============================================================
# HELPERS
# ============================================================

def print_separator():
    print("\n" + "=" * 70)


def has_description(description):
    """
    Returns True only when Description contains meaningful text.
    """

    if description is None:
        return False

    return bool(str(description).strip())


# ============================================================
# PROFILER
# ============================================================

def main():

    # --------------------------------------------------------
    # LOAD JOBS
    # --------------------------------------------------------

    jobs = get_jobs()

    results = []

    for row in jobs:

        classification = classify_job(row.JobTitle)

        results.append(
            {
                "job_posting_key": row.JobPostingKey,
                "source_system": row.SourceSystem,
                "source_job_id": row.SourceJobID,
                "job_title": row.JobTitle,
                "description": row.Description,
                **classification
            }
        )

    total_jobs = len(results)

    # --------------------------------------------------------
    # CLASSIFICATION STATUS
    # --------------------------------------------------------

    status_counts = Counter(
        row["is_tech_role"]
        for row in results
    )

    print_separator()
    print("JOB CLASSIFICATION V3 - DRY RUN")
    print("=" * 70)

    print(f"\nTotal jobs      : {total_jobs}")

    for status in [
        "Tech",
        "Non-Tech",
        "Ambiguous"
    ]:

        count = status_counts.get(status, 0)

        pct = (
            count / total_jobs * 100
            if total_jobs
            else 0
        )

        print(
            f"{status:<15}: "
            f"{count:>4} ({pct:>6.2f}%)"
        )

    # --------------------------------------------------------
    # SPLIT CLASSIFICATIONS
    # --------------------------------------------------------

    tech_rows = [
        row
        for row in results
        if row["is_tech_role"] == "Tech"
    ]

    non_tech_rows = [
        row
        for row in results
        if row["is_tech_role"] == "Non-Tech"
    ]

    ambiguous_rows = [
        row
        for row in results
        if row["is_tech_role"] == "Ambiguous"
    ]

    # --------------------------------------------------------
    # DESCRIPTION COVERAGE - ALL JOBS
    # --------------------------------------------------------

    all_jobs_with_description = [
        row
        for row in results
        if has_description(row["description"])
    ]

    all_description_count = len(
        all_jobs_with_description
    )

    all_description_pct = (
        all_description_count / total_jobs * 100
        if total_jobs
        else 0
    )

    print_separator()
    print("DESCRIPTION COVERAGE - ALL CANONICAL JOBS")
    print("=" * 70)

    print(f"\nTotal jobs           : {total_jobs}")
    print(
        f"With description     : "
        f"{all_description_count}"
    )
    print(
        f"Without description  : "
        f"{total_jobs - all_description_count}"
    )
    print(
        f"Description coverage : "
        f"{all_description_pct:.2f}%"
    )

    # --------------------------------------------------------
    # DESCRIPTION COVERAGE - AMBIGUOUS ONLY
    # --------------------------------------------------------

    ambiguous_with_description = [
        row
        for row in ambiguous_rows
        if has_description(row["description"])
    ]

    ambiguous_total = len(ambiguous_rows)

    ambiguous_description_count = len(
        ambiguous_with_description
    )

    ambiguous_description_pct = (
        ambiguous_description_count
        / ambiguous_total
        * 100
        if ambiguous_total
        else 0
    )

    print_separator()
    print("AMBIGUOUS DESCRIPTION COVERAGE")
    print("=" * 70)

    print(
        f"\nAmbiguous jobs       : "
        f"{ambiguous_total}"
    )
    print(
        f"With description     : "
        f"{ambiguous_description_count}"
    )
    print(
        f"Without description  : "
        f"{ambiguous_total - ambiguous_description_count}"
    )
    print(
        f"Description coverage : "
        f"{ambiguous_description_pct:.2f}%"
    )

    # --------------------------------------------------------
    # CAREER AREA DISTRIBUTION
    # --------------------------------------------------------

    print_separator()
    print("CAREER AREA DISTRIBUTION - TECH ONLY")
    print("=" * 70)

    career_area_counts = Counter(
        row["career_area"]
        for row in tech_rows
    )

    for career_area, count in (
        career_area_counts.most_common()
    ):

        pct = (
            count / len(tech_rows) * 100
            if tech_rows
            else 0
        )

        print(
            f"{career_area:<40}"
            f"{count:>5} "
            f"({pct:>6.2f}%)"
        )

    # --------------------------------------------------------
    # ROLE DISTRIBUTION
    # --------------------------------------------------------

    print_separator()
    print("ROLE DISTRIBUTION - TECH ONLY")
    print("=" * 70)

    role_counts = Counter(
        row["normalized_role"]
        for row in tech_rows
    )

    for role, count in role_counts.most_common():
        print(
            f"{role:<40}"
            f"{count:>5}"
        )

    # --------------------------------------------------------
    # CAREER AREA -> ROLE
    # --------------------------------------------------------

    print_separator()
    print("CAREER AREA -> ROLE")
    print("=" * 70)

    area_roles = defaultdict(Counter)

    for row in tech_rows:

        area_roles[
            row["career_area"]
        ][
            row["normalized_role"]
        ] += 1

    for career_area in sorted(area_roles):

        print(f"\n[{career_area}]")

        for role, count in (
            area_roles[
                career_area
            ].most_common()
        ):

            print(
                f"  {role:<38}"
                f"{count:>5}"
            )

    # --------------------------------------------------------
    # NON-TECH CATEGORY DISTRIBUTION
    # --------------------------------------------------------

    print_separator()
    print("NON-TECH CATEGORY DISTRIBUTION")
    print("=" * 70)

    non_tech_counts = Counter(
        row["non_tech_category"]
        for row in non_tech_rows
    )

    for category, count in (
        non_tech_counts.most_common()
    ):

        print(
            f"{category:<40}"
            f"{count:>5}"
        )

    # --------------------------------------------------------
    # SENIORITY DISTRIBUTION
    # --------------------------------------------------------

    print_separator()
    print("SENIORITY DISTRIBUTION - ALL JOBS")
    print("=" * 70)

    seniority_counts = Counter(
        row["seniority"]
        for row in results
    )

    for seniority, count in (
        seniority_counts.most_common()
    ):

        pct = (
            count / total_jobs * 100
            if total_jobs
            else 0
        )

        print(
            f"{seniority:<20}"
            f"{count:>5} "
            f"({pct:>6.2f}%)"
        )

    # --------------------------------------------------------
    # AMBIGUOUS TITLES
    # --------------------------------------------------------

    print_separator()
    print("AMBIGUOUS TITLES")
    print("=" * 70)

    ambiguous_title_counts = Counter(
        row["job_title"]
        for row in ambiguous_rows
    )

    print(
        f"\nDistinct ambiguous titles: "
        f"{len(ambiguous_title_counts)}\n"
    )

    for title, count in (
        ambiguous_title_counts.most_common()
    ):

        print(
            f"{count:>3} | {title}"
        )

    # --------------------------------------------------------
    # AMBIGUOUS JOBS WITHOUT DESCRIPTION
    # --------------------------------------------------------

    ambiguous_without_description = [
        row
        for row in ambiguous_rows
        if not has_description(
            row["description"]
        )
    ]

    print_separator()
    print("AMBIGUOUS JOBS WITHOUT DESCRIPTION")
    print("=" * 70)

    if not ambiguous_without_description:

        print(
            "\nAll ambiguous jobs have descriptions."
        )

    else:

        print(
            f"\nCount: "
            f"{len(ambiguous_without_description)}\n"
        )

        for row in ambiguous_without_description:

            print(
                f"{row['job_posting_key']:>5} | "
                f"{row['source_system']:<10} | "
                f"{row['job_title']}"
            )

    # --------------------------------------------------------
    # FINISH
    # --------------------------------------------------------

    print_separator()
    print(
        "DRY RUN COMPLETED - DATABASE NOT MODIFIED"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()