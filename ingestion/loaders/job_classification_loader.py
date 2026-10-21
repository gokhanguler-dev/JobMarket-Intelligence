import argparse
from collections import Counter

from ingestion.loaders.dwh_loader import get_connection
from ingestion.parsers.production_job_classifier import (
    classify_job_production,
)


# ============================================================
# SQL
# ============================================================

JOB_QUERY = """
SELECT
     f.JobPostingKey
    ,f.SourceSystem
    ,f.SourceJobID
    ,f.JobTitle
    ,f.RoleKey
    ,r.RoleName AS CurrentRoleName

    -- pyodbc / ODBC Driver 17 cannot reliably fetch
    -- DATETIMEOFFSET directly, so we do not select it here.

    ,s.Description

FROM dwh.FactJobPosting f

LEFT JOIN dwh.DimRole r
    ON r.RoleKey = f.RoleKey

OUTER APPLY
(
    SELECT TOP 1
         j.Description
    FROM stg.JobPosting j
    WHERE j.SourceSystem = f.SourceSystem
      AND j.SourceJobID = f.SourceJobID
    ORDER BY j.ExtractedAt DESC
) s

ORDER BY f.JobPostingKey;
"""


CAREER_AREA_QUERY = """
SELECT
     CareerAreaKey
    ,CareerAreaName
FROM dwh.DimCareerArea
WHERE IsActive = 1;
"""


ROLE_QUERY = """
SELECT
     RoleKey
    ,RoleName
FROM dwh.DimRole;
"""


UPDATE_QUERY = """
UPDATE dwh.FactJobPosting
SET
     IsTechRole = ?
    ,CareerAreaKey = ?
    ,RoleKey = ?
    ,Seniority = ?
    ,ClassificationConfidence = ?
    ,ClassificationVersion = ?
WHERE JobPostingKey = ?;
"""


# ============================================================
# LOAD CAREER AREA LOOKUP
# ============================================================

def load_career_area_lookup(cursor):

    cursor.execute(CAREER_AREA_QUERY)

    lookup = {}

    for row in cursor.fetchall():

        career_area_key = row[0]
        career_area_name = row[1]

        lookup[career_area_name] = career_area_key

    return lookup


# ============================================================
# LOAD ROLE LOOKUP
# ============================================================

def load_role_lookup(cursor):

    cursor.execute(ROLE_QUERY)

    lookup = {}

    for row in cursor.fetchall():

        role_key = row[0]
        role_name = row[1]

        lookup[role_name] = role_key

    return lookup


# ============================================================
# LOAD CANONICAL JOBS
# ============================================================

def load_jobs(cursor):

    cursor.execute(JOB_QUERY)

    jobs = []

    for row in cursor.fetchall():

        jobs.append(
            {
                "job_posting_key": row[0],
                "source_system": row[1],
                "source_job_id": row[2],
                "job_title": row[3],
                "current_role_key": row[4],
                "current_role_name": row[5],
                "description": row[6],
            }
        )

    return jobs


# ============================================================
# CLASSIFY
# ============================================================

def classify_jobs(
    jobs,
    career_area_lookup,
    role_lookup,
):

    results = []

    for job in jobs:

        classification = classify_job_production(
            job_title=job["job_title"],
            description=job["description"],
        )

        career_area_name = classification["career_area"]

        career_area_key = career_area_lookup.get(
            career_area_name
        )

        normalized_role = classification["normalized_role"]

        role_key = role_lookup.get(
            normalized_role
        )

        results.append(
            {
                **job,

                "is_tech_role":
                    classification["is_tech_role"],

                "career_area":
                    career_area_name,

                "career_area_key":
                    career_area_key,

                "normalized_role":
                    normalized_role,

                "role_key":
                    role_key,

                "seniority":
                    classification["seniority"],

                "confidence":
                    classification[
                        "classification_confidence"
                    ],

                "version":
                    classification[
                        "classification_version"
                    ],

                "stage":
                    classification[
                        "classification_stage"
                    ],

                "tech_score":
                    classification["tech_score"],

                "non_tech_score":
                    classification["non_tech_score"],

                "score_margin":
                    classification["score_margin"],
            }
        )

    return results


# ============================================================
# VALIDATION
# ============================================================

def validate_results(results):

    missing_career_area = [
        row
        for row in results
        if row["career_area_key"] is None
    ]

    missing_role = [
        row
        for row in results
        if row["role_key"] is None
    ]

    invalid_status = [
        row
        for row in results
        if row["is_tech_role"]
        not in {
            "Tech",
            "Non-Tech",
            "Ambiguous",
        }
    ]

    invalid_confidence = [
        row
        for row in results
        if row["confidence"]
        not in {
            "High",
            "Medium",
            "Low",
        }
    ]

    if missing_career_area:

        names = sorted(
            {
                row["career_area"]
                for row in missing_career_area
            }
        )

        raise ValueError(
            "CareerAreaKey not found for: "
            + ", ".join(names)
        )

    if missing_role:

        names = sorted(
            {
                row["normalized_role"]
                for row in missing_role
            }
        )

        raise ValueError(
            "RoleKey not found for normalized roles: "
            + ", ".join(names)
        )

    if invalid_status:

        raise ValueError(
            "Invalid classification status found."
        )

    if invalid_confidence:

        raise ValueError(
            "Invalid classification confidence found."
        )


# ============================================================
# PREVIEW
# ============================================================

def print_preview(results):

    status_counts = Counter(
        row["is_tech_role"]
        for row in results
    )

    area_counts = Counter(
        row["career_area"]
        for row in results
    )

    confidence_counts = Counter(
        row["confidence"]
        for row in results
    )

    stage_counts = Counter(
        row["stage"]
        for row in results
    )

    missing_description_count = sum(
        1
        for row in results
        if not row["description"]
    )

    missing_career_area_count = sum(
        1
        for row in results
        if row["career_area_key"] is None
    )

    missing_role_count = sum(
        1
        for row in results
        if row["role_key"] is None
    )

    role_changes = [
        row
        for row in results
        if row["current_role_name"]
        != row["normalized_role"]
    ]

    current_other_count = sum(
        1
        for row in results
        if row["is_tech_role"] == "Tech"
        and row["current_role_name"] == "Other"
    )

    new_other_count = sum(
        1
        for row in results
        if row["is_tech_role"] == "Tech"
        and row["normalized_role"] == "Other"
    )

    print()
    print("=" * 70)
    print("JOB CLASSIFICATION PREVIEW")
    print("=" * 70)

    print(
        f"Canonical jobs          : "
        f"{len(results)}"
    )

    print(
        f"Missing descriptions    : "
        f"{missing_description_count}"
    )

    print(
        f"Missing CareerAreaKey   : "
        f"{missing_career_area_count}"
    )

    print(
        f"Missing RoleKey         : "
        f"{missing_role_count}"
    )

    print()
    print("CLASSIFICATION STATUS")
    print("-" * 70)

    for name in (
        "Tech",
        "Non-Tech",
        "Ambiguous",
    ):

        print(
            f"{name:<25}: "
            f"{status_counts.get(name, 0)}"
        )

    print()
    print("CAREER AREA")
    print("-" * 70)

    for name, count in sorted(
        area_counts.items(),
        key=lambda item: (
            -item[1],
            item[0]
        )
    ):

        print(
            f"{name:<35}: "
            f"{count}"
        )

    print()
    print("CONFIDENCE")
    print("-" * 70)

    for name in (
        "High",
        "Medium",
        "Low",
    ):

        print(
            f"{name:<25}: "
            f"{confidence_counts.get(name, 0)}"
        )

    print()
    print("CLASSIFICATION STAGE")
    print("-" * 70)

    for name, count in sorted(
        stage_counts.items()
    ):

        print(
            f"{name:<25}: "
            f"{count}"
        )

    print()
    print("ROLE SYNCHRONIZATION")
    print("-" * 70)

    print(
        f"Role changes            : "
        f"{len(role_changes)}"
    )

    print(
        f"Tech Other - Before     : "
        f"{current_other_count}"
    )

    print(
        f"Tech Other - After      : "
        f"{new_other_count}"
    )

    print(
        f"Tech Other - Resolved   : "
        f"{current_other_count - new_other_count}"
    )

    print()
    print("ROLE CHANGE SUMMARY")
    print("-" * 70)

    role_change_counts = Counter(
        (
            row["current_role_name"] or "<NULL>",
            row["normalized_role"],
        )
        for row in role_changes
    )

    for (
        current_role,
        new_role,
    ), count in sorted(
        role_change_counts.items(),
        key=lambda item: (
            -item[1],
            item[0][0],
            item[0][1],
        )
    ):

        print(
            f"{count:>4} | "
            f"{current_role:<25} -> "
            f"{new_role}"
        )

    print()
    print("ROLE CHANGES - DETAIL")
    print("-" * 70)

    for row in role_changes:

        print(
            f"{row['job_posting_key']:>5} | "
            f"{(row['current_role_name'] or '<NULL>'):<22} -> "
            f"{row['normalized_role']:<25} | "
            f"{row['job_title']}"
        )

    print()
    print("V4.2 RESOLVED TECH JOBS")
    print("-" * 70)

    v42_tech = [
        row
        for row in results
        if row["stage"] == "V4.2 Evidence"
        and row["is_tech_role"] == "Tech"
    ]

    for row in v42_tech:

        print(
            f"{row['job_posting_key']:>5} | "
            f"{row['career_area']:<30} | "
            f"{row['confidence']:<6} | "
            f"{row['normalized_role']:<25} | "
            f"{row['job_title']}"
        )

    print()

    print(
        f"V4.2 Tech resolved      : "
        f"{len(v42_tech)}"
    )

    print("=" * 70)


# ============================================================
# APPLY
# ============================================================

def apply_results(
    cursor,
    results
):

    parameters = [
        (
            row["is_tech_role"],
            row["career_area_key"],
            row["role_key"],
            row["seniority"],
            row["confidence"],
            row["version"],
            row["job_posting_key"],
        )
        for row in results
    ]

    cursor.fast_executemany = True

    cursor.executemany(
        UPDATE_QUERY,
        parameters
    )


# ============================================================
# MAIN
# ============================================================

def run(apply_changes=False):

    connection = None
    cursor = None

    try:

        connection = get_connection()
        cursor = connection.cursor()

        career_area_lookup = (
            load_career_area_lookup(
                cursor
            )
        )

        role_lookup = (
            load_role_lookup(
                cursor
            )
        )

        jobs = load_jobs(
            cursor
        )

        results = classify_jobs(
            jobs,
            career_area_lookup,
            role_lookup,
        )

        validate_results(
            results
        )

        print_preview(
            results
        )

        if not apply_changes:

            connection.rollback()

            print()
            print(
                "PREVIEW ONLY - "
                "DATABASE NOT MODIFIED"
            )

            return

        apply_results(
            cursor,
            results
        )

        connection.commit()

        print()
        print("=" * 70)
        print(
            "CLASSIFICATION BACKFILL COMPLETED"
        )
        print("=" * 70)
        print(
            f"Rows processed : "
            f"{len(results)}"
        )
        print(
            "Database changes committed."
        )

    except Exception:

        if connection is not None:
            connection.rollback()

        raise

    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Classify canonical job postings "
            "using production classifier V4.2 "
            "and synchronize CareerAreaKey, "
            "RoleKey and Seniority."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Write classification results "
            "to dwh.FactJobPosting."
        )
    )

    args = parser.parse_args()

    run(
        apply_changes=args.apply
    )