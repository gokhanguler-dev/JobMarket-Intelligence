import argparse

from ingestion.loaders.dwh_loader import get_connection
from ingestion.parsers.capability_extractor import extract_capabilities


# ============================================================
# SQL
# ============================================================

JOB_QUERY = """
SELECT
     f.JobPostingKey
    ,f.SourceSystem
    ,f.SourceJobID
    ,f.JobTitle
    ,f.IsTechRole
    ,ca.CareerAreaName
    ,r.RoleName
    ,s.Description

FROM dwh.FactJobPosting f

LEFT JOIN dwh.DimCareerArea ca
    ON ca.CareerAreaKey = f.CareerAreaKey

LEFT JOIN dwh.DimRole r
    ON r.RoleKey = f.RoleKey

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

WHERE f.IsTechRole = 'Tech'

ORDER BY
    f.JobPostingKey;
"""


DELETE_QUERY = """
DELETE FROM stg.JobPostingCapability;
"""


INSERT_QUERY = """
INSERT INTO stg.JobPostingCapability
(
     SourceSystem
    ,SourceJobID
    ,CapabilityName
    ,CapabilityCategory
    ,Confidence
)
VALUES
(
    ?, ?, ?, ?, ?
);
"""


# ============================================================
# LOAD TECH JOBS
# ============================================================

def load_tech_jobs(cursor):

    cursor.execute(JOB_QUERY)

    jobs = []

    for row in cursor.fetchall():

        jobs.append(
            {
                "job_posting_key": row[0],
                "source_system": row[1],
                "source_job_id": row[2],
                "job_title": row[3],
                "is_tech_role": row[4],
                "career_area": row[5],
                "role_name": row[6],
                "description": row[7],
            }
        )

    return jobs


# ============================================================
# EXTRACT CAPABILITIES
# ============================================================

def extract_job_capabilities(jobs):

    results = []

    jobs_with_capability = 0
    jobs_without_capability = 0

    for index, job in enumerate(
        jobs,
        start=1
    ):

        # ----------------------------------------------------
        # CAPABILITY EXTRACTION
        #
        # Capability evidence is extracted only from the
        # standardized job description.
        #
        # Career Area and Role are used only as contextual
        # validation by Capability Taxonomy V1.2.
        #
        # This intentionally matches the production
        # capability coverage profiler.
        # ----------------------------------------------------

        capabilities = extract_capabilities(
            job["description"],
            career_area=job["career_area"],
            role_name=job["role_name"],
        )

        # ----------------------------------------------------
        # COVERAGE COUNTERS
        # ----------------------------------------------------

        if capabilities:
            jobs_with_capability += 1
        else:
            jobs_without_capability += 1

        # ----------------------------------------------------
        # FLATTEN ACCEPTED CAPABILITY RELATIONSHIPS
        # ----------------------------------------------------

        for capability in capabilities:

            results.append(
                {
                    "job_posting_key":
                        job["job_posting_key"],

                    "source_system":
                        job["source_system"],

                    "source_job_id":
                        job["source_job_id"],

                    "job_title":
                        job["job_title"],

                    "career_area":
                        job["career_area"],

                    "role_name":
                        job["role_name"],

                    "capability_name":
                        capability["capability"],

                    "capability_category":
                        capability["category"],

                    "confidence":
                        capability["confidence"],
                }
            )

        # ----------------------------------------------------
        # CONSOLE OUTPUT
        # ----------------------------------------------------

        print(
            f"[{index}/{len(jobs)}] "
            f"{job['job_title']}"
        )

        print(
            f"    Career Area : "
            f"{job['career_area']}"
        )

        print(
            f"    Role        : "
            f"{job['role_name']}"
        )

        capability_names = ", ".join(
            item["capability"]
            for item in capabilities
        )

        if not capability_names:
            capability_names = "NONE"

        print(
            f"    Capabilities: "
            f"{capability_names}"
        )

    return (
        results,
        jobs_with_capability,
        jobs_without_capability,
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_results(
    jobs,
    results,
):

    # --------------------------------------------------------
    # Every Tech job must have the required classification
    # context for deterministic capability evaluation.
    # --------------------------------------------------------

    invalid_jobs = [
        job
        for job in jobs
        if not job["source_system"]
        or not job["source_job_id"]
        or not job["career_area"]
        or not job["role_name"]
    ]

    if invalid_jobs:

        print()
        print("INVALID TECH JOBS")
        print("-" * 70)

        for job in invalid_jobs[:20]:

            print(
                f"{job['job_posting_key']} | "
                f"{job['job_title']} | "
                f"SourceSystem={job['source_system']} | "
                f"SourceJobID={job['source_job_id']} | "
                f"CareerArea={job['career_area']} | "
                f"Role={job['role_name']}"
            )

        raise ValueError(
            "Tech jobs with missing capability context found."
        )

    # --------------------------------------------------------
    # Capability Taxonomy V1.2 accepted confidence values
    # --------------------------------------------------------

    valid_confidence = {
        "Strong Role Context",
        "Strong Area Context",
        "Contextual Role",
    }

    invalid_confidence = [
        row
        for row in results
        if row["confidence"]
        not in valid_confidence
    ]

    if invalid_confidence:

        invalid_values = sorted(
            {
                row["confidence"]
                for row in invalid_confidence
            }
        )

        raise ValueError(
            "Invalid capability confidence found: "
            + ", ".join(invalid_values)
        )

    # --------------------------------------------------------
    # Validate natural-key uniqueness before SQL insert
    #
    # STG primary key:
    # SourceSystem + SourceJobID + CapabilityName
    # --------------------------------------------------------

    duplicate_keys = set()
    seen_keys = set()

    for row in results:

        key = (
            row["source_system"],
            row["source_job_id"],
            row["capability_name"],
        )

        if key in seen_keys:
            duplicate_keys.add(key)

        seen_keys.add(key)

    if duplicate_keys:

        print()
        print("DUPLICATE CAPABILITY KEYS")
        print("-" * 70)

        for key in sorted(duplicate_keys)[:20]:

            print(
                f"{key[0]} | "
                f"{key[1]} | "
                f"{key[2]}"
            )

        raise ValueError(
            "Duplicate capability relationships found: "
            f"{len(duplicate_keys)}"
        )


# ============================================================
# PREVIEW SUMMARY
# ============================================================

def print_summary(
    jobs,
    results,
    jobs_with_capability,
    jobs_without_capability,
):

    if jobs:

        coverage = (
            jobs_with_capability
            / len(jobs)
            * 100
        )

    else:
        coverage = 0

    print()
    print("=" * 70)
    print(
        "CAPABILITY STAGING PREVIEW - V1.2"
    )
    print("=" * 70)

    print(
        f"Tech jobs               : "
        f"{len(jobs)}"
    )

    print(
        f"Jobs with capability    : "
        f"{jobs_with_capability}"
    )

    print(
        f"Jobs without capability : "
        f"{jobs_without_capability}"
    )

    print(
        f"Capability relationships: "
        f"{len(results)}"
    )

    print(
        f"Coverage                 : "
        f"{coverage:.2f}%"
    )

    print("=" * 70)


# ============================================================
# APPLY
# ============================================================

def apply_results(
    cursor,
    results,
):

    # --------------------------------------------------------
    # FULL REFRESH
    #
    # Capability extraction depends on:
    #
    # - Capability Taxonomy
    # - Capability Context
    # - Career Area
    # - Normalized Role
    #
    # If any of these rules change, previously accepted
    # capability relationships may become invalid.
    #
    # Therefore the capability staging table is rebuilt from
    # the current canonical Tech job population.
    # --------------------------------------------------------

    cursor.execute(
        DELETE_QUERY
    )

    if not results:
        return

    parameters = [
        (
            row["source_system"],
            row["source_job_id"],
            row["capability_name"],
            row["capability_category"],
            row["confidence"],
        )
        for row in results
    ]

    cursor.fast_executemany = True

    cursor.executemany(
        INSERT_QUERY,
        parameters
    )


# ============================================================
# MAIN
# ============================================================

def run(apply_changes=False):

    connection = None
    cursor = None

    try:

        # ----------------------------------------------------
        # DATABASE CONNECTION
        # ----------------------------------------------------

        connection = get_connection()
        cursor = connection.cursor()

        # ----------------------------------------------------
        # 1. LOAD CANONICAL TECH JOBS
        #
        # Classification has already been persisted to
        # dwh.FactJobPosting by the production classifier.
        # ----------------------------------------------------

        jobs = load_tech_jobs(
            cursor
        )

        print()
        print("=" * 70)
        print(
            "CAPABILITY STAGING LOAD - V1.2"
        )
        print("=" * 70)

        print(
            f"Canonical Tech jobs loaded: "
            f"{len(jobs)}"
        )

        print()

        # ----------------------------------------------------
        # 2. EXTRACT ACCEPTED V1.2 CAPABILITIES
        # ----------------------------------------------------

        (
            results,
            jobs_with_capability,
            jobs_without_capability,
        ) = extract_job_capabilities(
            jobs
        )

        # ----------------------------------------------------
        # 3. VALIDATE
        # ----------------------------------------------------

        validate_results(
            jobs,
            results,
        )

        # ----------------------------------------------------
        # 4. PRINT SUMMARY
        # ----------------------------------------------------

        print_summary(
            jobs,
            results,
            jobs_with_capability,
            jobs_without_capability,
        )

        # ----------------------------------------------------
        # 5. PREVIEW MODE
        # ----------------------------------------------------

        if not apply_changes:

            connection.rollback()

            print()
            print(
                "PREVIEW ONLY - "
                "DATABASE NOT MODIFIED"
            )

            return

        # ----------------------------------------------------
        # 6. APPLY FULL REFRESH
        # ----------------------------------------------------

        apply_results(
            cursor,
            results,
        )

        connection.commit()

        print()
        print("=" * 70)
        print(
            "CAPABILITY STAGING LOAD COMPLETED"
        )
        print("=" * 70)

        print(
            f"Tech jobs processed      : "
            f"{len(jobs)}"
        )

        print(
            f"Jobs with capability     : "
            f"{jobs_with_capability}"
        )

        print(
            f"Jobs without capability  : "
            f"{jobs_without_capability}"
        )

        print(
            f"Capability relationships : "
            f"{len(results)}"
        )

        print(
            "Database changes committed."
        )

    except Exception as error:

        if connection is not None:
            connection.rollback()

        print()
        print("=" * 70)
        print(
            "CAPABILITY STAGING LOAD FAILED"
        )
        print("=" * 70)

        print(
            "Transaction rolled back."
        )

        print(error)

        raise

    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Extract Capability Taxonomy V1.2 "
            "relationships from canonical Tech jobs "
            "and load stg.JobPostingCapability."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Full-refresh "
            "stg.JobPostingCapability."
        )
    )

    args = parser.parse_args()

    run(
        apply_changes=args.apply
    )