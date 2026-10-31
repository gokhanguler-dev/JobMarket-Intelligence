import os
from pathlib import Path

import pyodbc
from config.env_loader import load_project_env

from ingestion.parsers.job_text_parser import clean_html_text
from ingestion.parsers.skill_extractor import extract_skills
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


# ============================================================
# DATABASE CONNECTION
# ============================================================

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
# REFRESH EXISTING STANDARDIZED FIELDS
# ============================================================

def refresh_existing_jobs(cursor):
    """
    Refresh standardized fields in already processed STG rows
    from their corresponding RAW observations.

    This is intentionally separate from skill extraction and
    classification because those values have already been
    calculated for existing observations.
    """

    cursor.execute(
        """
        UPDATE p
        SET
            p.SourcePlatform = r.SourcePlatform,
            p.Description = r.Description,
            p.WorkModel = r.WorkModel,

            p.SourceCreatedAt =
                CAST(r.SourceCreatedAt AS DATETIME2(7)),

            p.SourceUpdatedAt =
                CAST(r.SourceUpdatedAt AS DATETIME2(7)),

            p.ExtractedAt =
                CAST(r.ExtractedAt AS DATETIME2(7))

        FROM stg.JobPosting p

        INNER JOIN stg.JobPostingRaw r
            ON r.RawJobPostingID = p.RawJobPostingID;
        """
    )

    return cursor.rowcount


# ============================================================
# GET UNPROCESSED RAW JOBS
# ============================================================

def get_unprocessed_jobs(cursor):

    query = """
        SELECT
            r.RawJobPostingID,
            r.SourceJobID,
            r.SourceSystem,
            r.SourcePlatform,

            r.SearchKeyword,
            r.SearchLocation,

            r.JobTitle,
            r.Company,
            r.JobLocation,

            r.Description,

            r.Salary,
            r.EmploymentType,
            r.WorkModel,
            r.JobLink,

            CAST(
                r.SourceCreatedAt AS DATETIME2(7)
            ) AS SourceCreatedAt,

            CAST(
                r.SourceUpdatedAt AS DATETIME2(7)
            ) AS SourceUpdatedAt,

            CAST(
                r.ExtractedAt AS DATETIME2(7)
            ) AS ExtractedAt

        FROM stg.JobPostingRaw r

        LEFT JOIN stg.JobPosting p
            ON p.RawJobPostingID = r.RawJobPostingID

        WHERE p.RawJobPostingID IS NULL

        ORDER BY
            r.RawJobPostingID;
    """

    cursor.execute(query)

    return cursor.fetchall()


# ============================================================
# TRANSFORM AND LOAD
# ============================================================

def process_jobs():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # =====================================================
        # 1. REFRESH EXISTING PROCESSED OBSERVATIONS
        # =====================================================

        refreshed_count = refresh_existing_jobs(
            cursor
        )

        # =====================================================
        # 2. FIND NEW RAW OBSERVATIONS
        # =====================================================

        jobs = get_unprocessed_jobs(
            cursor
        )

        print()
        print("=" * 70)
        print("STG JOB TRANSFORMATION")
        print("=" * 70)
        print(
            f"Existing jobs refreshed : {refreshed_count}"
        )
        print(
            f"Unprocessed jobs        : {len(jobs)}"
        )
        print()

        insert_job_sql = """
            INSERT INTO stg.JobPosting
            (
                RawJobPostingID,
                SourceJobID,
                SourceSystem,
                SourcePlatform,

                SearchKeyword,
                SearchLocation,

                JobTitle,
                Company,
                JobLocation,

                CleanSnippet,
                Description,

                Salary,
                EmploymentType,
                WorkModel,
                JobLink,

                SourceCreatedAt,
                SourceUpdatedAt,
                ExtractedAt,

                NormalizedRole,
                Seniority
            )
            OUTPUT INSERTED.JobPostingStgID
            VALUES
            (
                ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?
            );
        """

        insert_skill_sql = """
            INSERT INTO stg.JobPostingSkill
            (
                JobPostingStgID,
                SkillName
            )
            VALUES
            (
                ?, ?
            );
        """

        processed_count = 0
        skill_count = 0

        # =====================================================
        # 3. PROCESS NEW OBSERVATIONS
        # =====================================================

        for job in jobs:

            # -------------------------------------------------
            # CLEAN STANDARDIZED DESCRIPTION
            # -------------------------------------------------

            clean_description = clean_html_text(
                job.Description
            )

            # -------------------------------------------------
            # SKILL EXTRACTION
            # -------------------------------------------------

            analysis_text = " ".join(
                filter(
                    None,
                    [
                        job.JobTitle,
                        clean_description
                    ]
                )
            )

            skills = extract_skills(
                analysis_text
            )

            # -------------------------------------------------
            # ROLE / SENIORITY CLASSIFICATION
            # -------------------------------------------------

            classification = classify_job(
                job.JobTitle
            )

            normalized_role = (
                classification["normalized_role"]
            )

            seniority = (
                classification["seniority"]
            )

            # -------------------------------------------------
            # INSERT PROCESSED JOB
            # -------------------------------------------------

            cursor.execute(
                insert_job_sql,

                job.RawJobPostingID,
                job.SourceJobID,
                job.SourceSystem,
                job.SourcePlatform,

                job.SearchKeyword,
                job.SearchLocation,

                job.JobTitle,
                job.Company,
                job.JobLocation,

                # Legacy CleanSnippet retained temporarily.
                clean_description,

                # Standardized field.
                clean_description,

                job.Salary,
                job.EmploymentType,
                job.WorkModel,
                job.JobLink,

                job.SourceCreatedAt,
                job.SourceUpdatedAt,
                job.ExtractedAt,

                normalized_role,
                seniority
            )

            inserted_row = cursor.fetchone()

            job_posting_stg_id = (
                inserted_row.JobPostingStgID
            )

            # -------------------------------------------------
            # INSERT SKILLS
            # -------------------------------------------------

            for skill in skills:

                cursor.execute(
                    insert_skill_sql,
                    job_posting_stg_id,
                    skill
                )

                skill_count += 1

            processed_count += 1

            print(
                f"[{processed_count}/{len(jobs)}] "
                f"{job.JobTitle}"
            )

            print(
                f"    Role      : {normalized_role}"
            )

            print(
                f"    Seniority : {seniority}"
            )

            print(
                f"    Skills    : "
                f"{', '.join(skills) if skills else 'NONE'}"
            )

        # =====================================================
        # COMMIT COMPLETE BATCH
        # =====================================================

        connection.commit()

        print()
        print("=" * 70)
        print("TRANSFORMATION COMPLETED")
        print("=" * 70)
        print(
            f"Existing jobs refreshed : {refreshed_count}"
        )
        print(
            f"New jobs processed      : {processed_count}"
        )
        print(
            f"New skills inserted     : {skill_count}"
        )

    except Exception as error:

        connection.rollback()

        print()
        print("=" * 70)
        print("TRANSFORMATION FAILED")
        print("=" * 70)
        print(
            "Transaction rolled back."
        )
        print(error)

        raise

    finally:

        cursor.close()
        connection.close()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    process_jobs()