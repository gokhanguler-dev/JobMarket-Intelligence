from ingestion.loaders.dwh_loader import get_connection
from ingestion.parsers.skill_extractor import extract_skills


# ============================================================
# LOAD EXISTING STG JOBS
# ============================================================

def load_existing_jobs(cursor):

    cursor.execute(
        """
        SELECT
             JobPostingStgID
            ,JobTitle
            ,Description
        FROM stg.JobPosting
        ORDER BY JobPostingStgID;
        """
    )

    return cursor.fetchall()


# ============================================================
# REBUILD SKILLS
# ============================================================

def rebuild_skills():

    connection = None
    cursor = None

    try:

        connection = get_connection()
        cursor = connection.cursor()

        jobs = load_existing_jobs(cursor)

        print()
        print("=" * 70)
        print("SKILL REBUILD STARTED")
        print("=" * 70)
        print(f"STG jobs found : {len(jobs)}")
        print()

        # ====================================================
        # 1. DELETE EXISTING STG SKILL RELATIONSHIPS
        # ====================================================

        cursor.execute(
            """
            DELETE FROM stg.JobPostingSkill;
            """
        )

        deleted_count = cursor.rowcount

        print(
            f"Existing skill rows deleted : {deleted_count}"
        )

        # ====================================================
        # 2. PREPARE INSERT
        # ====================================================

        insert_sql = """
            INSERT INTO stg.JobPostingSkill
            (
                 JobPostingStgID
                ,SkillName
            )
            VALUES
            (
                ?, ?
            );
        """

        inserted_skill_count = 0
        jobs_with_skills = 0
        jobs_without_skills = 0

        # ====================================================
        # 3. RE-EXTRACT SKILLS USING CURRENT TAXONOMY
        # ====================================================

        for index, job in enumerate(
            jobs,
            start=1
        ):

            title = (
                job.JobTitle
                if job.JobTitle
                else ""
            )

            description = (
                job.Description
                if job.Description
                else ""
            )

            analysis_text = " ".join(
                filter(
                    None,
                    [
                        title,
                        description
                    ]
                )
            )

            skills = extract_skills(
                analysis_text
            )

            if skills:

                jobs_with_skills += 1

            else:

                jobs_without_skills += 1

            for skill in skills:

                cursor.execute(
                    insert_sql,
                    job.JobPostingStgID,
                    skill
                )

                inserted_skill_count += 1

            if (
                index % 100 == 0
                or index == len(jobs)
            ):

                print(
                    f"Processed {index}/{len(jobs)} jobs"
                )

        # ====================================================
        # 4. COMMIT
        # ====================================================

        connection.commit()

        print()
        print("=" * 70)
        print("SKILL REBUILD COMPLETED")
        print("=" * 70)

        print(
            f"Jobs processed            : {len(jobs)}"
        )

        print(
            f"Jobs with skills          : {jobs_with_skills}"
        )

        print(
            f"Jobs without skills       : {jobs_without_skills}"
        )

        print(
            f"Skill relationships       : {inserted_skill_count}"
        )

    except Exception as error:

        if connection is not None:
            connection.rollback()

        print()
        print("=" * 70)
        print("SKILL REBUILD FAILED")
        print("=" * 70)
        print("Transaction rolled back.")
        print(error)

        raise

    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    rebuild_skills()