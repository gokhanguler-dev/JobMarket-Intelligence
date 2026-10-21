from collections import Counter, defaultdict

from ingestion.loaders.dwh_loader import get_connection
from ingestion.parsers.capability_extractor import (
    extract_capabilities,
    extract_capability_candidates,
)


# ------------------------------------------------------------
# DATA
# ------------------------------------------------------------

def get_tech_jobs():
    query = """
    SELECT
         f.JobPostingKey
        ,f.JobTitle
        ,ca.CareerAreaName
        ,r.RoleName
        ,f.Seniority
        ,latest.Description
    FROM dwh.FactJobPosting f

    LEFT JOIN dwh.DimCareerArea ca
        ON ca.CareerAreaKey = f.CareerAreaKey

    LEFT JOIN dwh.DimRole r
        ON r.RoleKey = f.RoleKey

    OUTER APPLY
    (
        SELECT TOP 1
            jp.Description
        FROM stg.JobPosting jp
        WHERE jp.SourceSystem = f.SourceSystem
          AND jp.SourceJobID = f.SourceJobID
        ORDER BY
             jp.ExtractedAt DESC
            ,jp.JobPostingStgID DESC
    ) latest

    WHERE f.IsTechRole = 'Tech'

    ORDER BY
        f.JobPostingKey;
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(query)

        columns = [
            column[0]
            for column in cursor.description
        ]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


# ------------------------------------------------------------
# PROFILE
# ------------------------------------------------------------

def main():

    jobs = get_tech_jobs()

    jobs_with_description = 0
    jobs_with_capability = 0
    jobs_without_capability = 0
    jobs_with_rejected_candidates = 0

    capability_jobs = defaultdict(set)
    category_jobs = defaultdict(set)
    area_capability_jobs = defaultdict(set)

    capability_examples = defaultdict(list)

    capability_count_per_job = Counter()
    confidence_counter = Counter()

    no_match_examples = []
    rejected_candidate_examples = []

    # --------------------------------------------------------
    # PROCESS JOBS
    # --------------------------------------------------------

    for job in jobs:

        job_key = job["JobPostingKey"]
        description = job.get("Description")
        career_area = job.get("CareerAreaName")
        role_name = job.get("RoleName")

        if description:
            jobs_with_description += 1

        # ----------------------------------------------------
        # V1.1 CONTEXT-AWARE EXTRACTION
        # ----------------------------------------------------

        matches = extract_capabilities(
            description,
            career_area=career_area,
            role_name=role_name,
        )

        candidates = extract_capability_candidates(
            description,
            career_area=career_area,
            role_name=role_name,
        )

        capability_count_per_job[len(matches)] += 1

        # ----------------------------------------------------
        # ACCEPTED CAPABILITIES
        # ----------------------------------------------------

        if matches:

            jobs_with_capability += 1

            for match in matches:

                capability = match["capability"]
                category = match["category"]
                confidence = match["confidence"]

                capability_jobs[capability].add(
                    job_key
                )

                category_jobs[category].add(
                    job_key
                )

                area_capability_jobs[
                    (
                        career_area,
                        capability,
                    )
                ].add(
                    job_key
                )

                confidence_counter[
                    confidence
                ] += 1

                if (
                    len(
                        capability_examples[
                            capability
                        ]
                    )
                    < 3
                ):

                    capability_examples[
                        capability
                    ].append(
                        (
                            job.get("JobTitle"),
                            career_area,
                            role_name,
                            confidence,
                            match["evidence_type"],
                            match["strong_matches"],
                            match["medium_matches"],
                            match["area_match"],
                            match["role_match"],
                        )
                    )

        # ----------------------------------------------------
        # NO ACCEPTED CAPABILITY
        # ----------------------------------------------------

        else:

            jobs_without_capability += 1

            if candidates:

                jobs_with_rejected_candidates += 1

                if (
                    len(
                        rejected_candidate_examples
                    )
                    < 25
                ):

                    rejected_candidate_examples.append(
                        (
                            job.get("JobTitle"),
                            career_area,
                            role_name,
                            candidates,
                        )
                    )

            elif (
                len(no_match_examples)
                < 25
            ):

                no_match_examples.append(
                    (
                        job.get("JobTitle"),
                        career_area,
                        role_name,
                    )
                )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print(
        "CAPABILITY TAXONOMY V1.1 "
        "- CONTEXT-AWARE COVERAGE PROFILE"
    )
    print("=" * 100)

    print(
        f"Tech jobs                  : "
        f"{len(jobs)}"
    )

    print(
        f"Jobs with description      : "
        f"{jobs_with_description}"
    )

    print(
        f"Jobs with capability       : "
        f"{jobs_with_capability}"
    )

    print(
        f"Jobs without capability    : "
        f"{jobs_without_capability}"
    )

    print(
        f"Rejected-candidate jobs    : "
        f"{jobs_with_rejected_candidates}"
    )

    if jobs:

        coverage = (
            jobs_with_capability
            / len(jobs)
            * 100
        )

    else:
        coverage = 0

    print(
        f"Context-aware coverage     : "
        f"{coverage:.2f}%"
    )

    # --------------------------------------------------------
    # CONFIDENCE DISTRIBUTION
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("CONFIDENCE DISTRIBUTION")
    print("=" * 100)

    for (
        confidence,
        count,
    ) in confidence_counter.most_common():

        print(
            f"{confidence:30}"
            f"{count:>5}"
        )

    # --------------------------------------------------------
    # CAPABILITY DISTRIBUTION
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("CAPABILITY DISTRIBUTION")
    print("=" * 100)

    sorted_capabilities = sorted(
        capability_jobs.items(),
        key=lambda item: (
            -len(item[1]),
            item[0],
        )
    )

    for (
        capability,
        job_keys,
    ) in sorted_capabilities:

        print(
            f"{capability:45}"
            f"{len(job_keys):>5}"
        )

    # --------------------------------------------------------
    # CATEGORY DISTRIBUTION
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("CATEGORY DISTRIBUTION")
    print("=" * 100)

    sorted_categories = sorted(
        category_jobs.items(),
        key=lambda item: (
            -len(item[1]),
            item[0],
        )
    )

    for (
        category,
        job_keys,
    ) in sorted_categories:

        print(
            f"{category:30}"
            f"{len(job_keys):>5}"
        )

    # --------------------------------------------------------
    # CAPABILITIES PER JOB
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("CAPABILITIES PER JOB")
    print("=" * 100)

    for count in sorted(
        capability_count_per_job
    ):

        print(
            f"{count:>2} capabilities : "
            f"{capability_count_per_job[count]:>4} jobs"
        )

    # --------------------------------------------------------
    # CAPABILITY MATCH EXAMPLES
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("CAPABILITY MATCH EXAMPLES")
    print("=" * 100)

    for (
        capability,
        job_keys,
    ) in sorted_capabilities:

        print()
        print(
            f"{capability} "
            f"({len(job_keys)} jobs)"
        )

        for (
            title,
            career_area,
            role_name,
            confidence,
            evidence_type,
            strong_matches,
            medium_matches,
            area_match,
            role_match,
        ) in capability_examples[
            capability
        ]:

            print(
                f"    - [{career_area}] "
                f"{title}"
            )

            print(
                f"      Role       : "
                f"{role_name}"
            )

            print(
                f"      Confidence : "
                f"{confidence}"
            )

            print(
                f"      Evidence   : "
                f"{evidence_type}"
            )

            if strong_matches:

                print(
                    f"      Strong     : "
                    f"{', '.join(strong_matches)}"
                )

            if medium_matches:

                print(
                    f"      Medium     : "
                    f"{', '.join(medium_matches)}"
                )

            print(
                f"      AreaMatch  : "
                f"{area_match}"
            )

            print(
                f"      RoleMatch  : "
                f"{role_match}"
            )

    # --------------------------------------------------------
    # REJECTED CANDIDATES
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("REJECTED CANDIDATE EXAMPLES")
    print("=" * 100)

    for (
        title,
        career_area,
        role_name,
        candidates,
    ) in rejected_candidate_examples:

        print()
        print(
            f"[{career_area}] "
            f"{title}"
        )

        print(
            f"    Role: "
            f"{role_name}"
        )

        for candidate in candidates:

            print(
                f"    Candidate : "
                f"{candidate['capability']}"
            )

            print(
                f"    Reason    : "
                f"{candidate['rejection_reason']}"
            )

            if candidate[
                "strong_matches"
            ]:

                print(
                    f"    Strong    : "
                    f"{', '.join(candidate['strong_matches'])}"
                )

            if candidate[
                "medium_matches"
            ]:

                print(
                    f"    Medium    : "
                    f"{', '.join(candidate['medium_matches'])}"
                )

    # --------------------------------------------------------
    # NO MATCH
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("NO CAPABILITY MATCH EXAMPLES")
    print("=" * 100)

    for (
        title,
        career_area,
        role_name,
    ) in no_match_examples:

        print(
            f"[{career_area}] "
            f"{title} "
            f"| Role={role_name}"
        )


if __name__ == "__main__":
    main()