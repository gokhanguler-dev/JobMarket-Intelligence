import os
from collections import Counter

import pyodbc
from dotenv import load_dotenv

from ingestion.parsers.job_classifier import classify_job
from ingestion.parsers.description_evidence import (
    classify_description,
    format_matches
)


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

    query = """
        SELECT
            f.JobPostingKey,
            f.SourceSystem,
            f.SourceJobID,
            f.JobTitle,
            f.CompanyKey,
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

def separator():
    print("\n" + "=" * 90)


def get_top_area_scores(area_scores, limit=3):

    return sorted(
        area_scores.items(),
        key=lambda item: item[1],
        reverse=True
    )[:limit]


def print_match_line(label, matches):

    if not matches:
        return

    formatted = format_matches(matches)

    if formatted and formatted != "-":
        print(f"{label:<13}: {formatted}")


# ============================================================
# MAIN
# ============================================================

def main():

    jobs = get_jobs()

    # --------------------------------------------------------
    # V3 TITLE CLASSIFICATION
    # --------------------------------------------------------

    title_results = []

    for row in jobs:

        title_classification = classify_job(
            row.JobTitle
        )

        title_results.append(
            {
                "job_posting_key": row.JobPostingKey,
                "source_system": row.SourceSystem,
                "source_job_id": row.SourceJobID,
                "job_title": row.JobTitle,
                "description": row.Description,
                **title_classification
            }
        )

    ambiguous_rows = [
        row
        for row in title_results
        if row["is_tech_role"] == "Ambiguous"
    ]

    # --------------------------------------------------------
    # V4.1 EVIDENCE CLASSIFICATION
    #
    # IMPORTANT:
    # Only V3-Ambiguous jobs reach this stage.
    #
    # V4.1 uses:
    #   - title tech evidence
    #   - description career-area evidence
    #   - description generic-tech evidence
    #   - description non-tech evidence
    # --------------------------------------------------------

    v41_results = []

    for row in ambiguous_rows:

        evidence = classify_description(
            description=row["description"],
            title=row["job_title"]
        )

        v41_results.append(
            {
                **row,

                "evidence_classification":
                    evidence["classification"],

                "evidence_career_area":
                    evidence["career_area"],

                "tech_score":
                    evidence["tech_score"],

                "non_tech_score":
                    evidence["non_tech_score"],

                "score_margin":
                    evidence["margin"],

                "confidence":
                    evidence["confidence"],

                "title_tech_score":
                    evidence["title_tech_score"],

                "generic_tech_score":
                    evidence["generic_tech_score"],

                "top_career_area":
                    evidence["top_career_area"],

                "top_career_area_score":
                    evidence["top_career_area_score"],

                "career_area_scores":
                    evidence["career_area_scores"],

                "career_area_matches":
                    evidence["career_area_matches"],

                "title_tech_matches":
                    evidence["title_tech_matches"],

                "generic_tech_matches":
                    evidence["generic_tech_matches"],

                "non_tech_matches":
                    evidence["non_tech_matches"]
            }
        )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    separator()

    print("JOB CLASSIFICATION V4.1 - EVIDENCE DRY RUN")
    print("=" * 90)

    print(f"\nCanonical jobs       : {len(jobs)}")
    print(
        f"V3 ambiguous jobs    : "
        f"{len(ambiguous_rows)}"
    )

    result_counts = Counter(
        row["evidence_classification"]
        for row in v41_results
    )

    separator()

    print("V4.1 AMBIGUOUS RESOLUTION")
    print("=" * 90)

    for classification in [
        "Tech",
        "Non-Tech",
        "Ambiguous"
    ]:

        count = result_counts.get(
            classification,
            0
        )

        pct = (
            count / len(v41_results) * 100
            if v41_results
            else 0
        )

        print(
            f"{classification:<15}"
            f"{count:>5} "
            f"({pct:>6.2f}%)"
        )

    # --------------------------------------------------------
    # V4 BASELINE COMPARISON
    # --------------------------------------------------------

    separator()

    print("V4 -> V4.1 COMPARISON")
    print("=" * 90)

    v4_baseline = {
        "Tech": 5,
        "Non-Tech": 11,
        "Ambiguous": 103
    }

    for classification in [
        "Tech",
        "Non-Tech",
        "Ambiguous"
    ]:

        old_count = v4_baseline[classification]
        new_count = result_counts.get(
            classification,
            0
        )

        difference = new_count - old_count

        print(
            f"{classification:<15}"
            f"V4={old_count:>4}   "
            f"V4.1={new_count:>4}   "
            f"Delta={difference:>+4}"
        )

    # --------------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------------

    separator()

    print("CONFIDENCE DISTRIBUTION")
    print("=" * 90)

    confidence_counts = Counter(
        row["confidence"]
        for row in v41_results
    )

    for confidence in [
        "High",
        "Medium",
        "Low"
    ]:

        print(
            f"{confidence:<15}"
            f"{confidence_counts.get(confidence, 0):>5}"
        )

    # --------------------------------------------------------
    # TECH CAREER AREA DISTRIBUTION
    # --------------------------------------------------------

    tech_results = [
        row
        for row in v41_results
        if row["evidence_classification"] == "Tech"
    ]

    separator()

    print("NEW TECH JOBS BY CAREER AREA")
    print("=" * 90)

    career_area_counts = Counter(
        row["evidence_career_area"]
        for row in tech_results
    )

    if not career_area_counts:

        print("\nNo ambiguous jobs resolved as Tech.")

    else:

        print()

        for area, count in career_area_counts.most_common():

            print(
                f"{area:<40}"
                f"{count:>5}"
            )

    # --------------------------------------------------------
    # DETAIL - TECH
    # --------------------------------------------------------

    separator()

    print("RESOLVED AS TECH")
    print("=" * 90)

    if not tech_results:

        print("\nNone.")

    else:

        for row in sorted(
            tech_results,
            key=lambda x: (
                -x["score_margin"],
                x["job_title"]
            )
        ):

            print(
                f"\nTITLE       : "
                f"{row['job_title']}"
            )

            print(
                f"SOURCE      : "
                f"{row['source_system']}"
            )

            print(
                f"CAREER AREA : "
                f"{row['evidence_career_area']}"
            )

            print(
                f"TECH SCORE  : "
                f"{row['tech_score']}"
            )

            print(
                f"NON-TECH    : "
                f"{row['non_tech_score']}"
            )

            print(
                f"MARGIN      : "
                f"{row['score_margin']}"
            )

            print(
                f"CONFIDENCE  : "
                f"{row['confidence']}"
            )

            print(
                f"TITLE SCORE : "
                f"{row['title_tech_score']}"
            )

            print(
                f"GENERIC     : "
                f"{row['generic_tech_score']}"
            )

            print("TOP AREAS   :")

            for area, score in get_top_area_scores(
                row["career_area_scores"]
            ):

                if score > 0:

                    print(
                        f"    {area}: {score}"
                    )

            print_match_line(
                "TITLE EV",
                row["title_tech_matches"]
            )

            selected_area = row["evidence_career_area"]

            if selected_area not in [
                "Other Tech",
                "Unknown",
                "Out of Scope"
            ]:

                area_matches = (
                    row["career_area_matches"]
                    .get(
                        selected_area,
                        []
                    )
                )

                print_match_line(
                    "AREA EV",
                    area_matches
                )

            print_match_line(
                "GENERIC EV",
                row["generic_tech_matches"]
            )

            print_match_line(
                "NON-TECH EV",
                row["non_tech_matches"]
            )

            print("-" * 90)

    # --------------------------------------------------------
    # DETAIL - NON TECH
    # --------------------------------------------------------

    non_tech_results = [
        row
        for row in v41_results
        if row["evidence_classification"] == "Non-Tech"
    ]

    separator()

    print("RESOLVED AS NON-TECH")
    print("=" * 90)

    if not non_tech_results:

        print("\nNone.")

    else:

        for row in sorted(
            non_tech_results,
            key=lambda x: (
                -x["score_margin"],
                x["job_title"]
            )
        ):

            print(
                f"\nTITLE       : "
                f"{row['job_title']}"
            )

            print(
                f"SOURCE      : "
                f"{row['source_system']}"
            )

            print(
                f"TECH SCORE  : "
                f"{row['tech_score']}"
            )

            print(
                f"NON-TECH    : "
                f"{row['non_tech_score']}"
            )

            print(
                f"MARGIN      : "
                f"{row['score_margin']}"
            )

            print(
                f"CONFIDENCE  : "
                f"{row['confidence']}"
            )

            print(
                f"TITLE SCORE : "
                f"{row['title_tech_score']}"
            )

            print_match_line(
                "TITLE EV",
                row["title_tech_matches"]
            )

            print_match_line(
                "NON-TECH EV",
                row["non_tech_matches"]
            )

            print("-" * 90)

    # --------------------------------------------------------
    # STILL AMBIGUOUS
    # --------------------------------------------------------

    still_ambiguous = [
        row
        for row in v41_results
        if row["evidence_classification"] == "Ambiguous"
    ]

    separator()

    print("STILL AMBIGUOUS")
    print("=" * 90)

    if not still_ambiguous:

        print("\nNone.")

    else:

        for row in sorted(
            still_ambiguous,
            key=lambda x: (
                -max(
                    x["tech_score"],
                    x["non_tech_score"]
                ),
                x["job_title"]
            )
        ):

            print(
                f"\nTITLE       : "
                f"{row['job_title']}"
            )

            print(
                f"SOURCE      : "
                f"{row['source_system']}"
            )

            print(
                f"TECH SCORE  : "
                f"{row['tech_score']}"
            )

            print(
                f"NON-TECH    : "
                f"{row['non_tech_score']}"
            )

            print(
                f"MARGIN      : "
                f"{row['score_margin']}"
            )

            print(
                f"TITLE SCORE : "
                f"{row['title_tech_score']}"
            )

            top_areas = [
                f"{area}={score}"
                for area, score
                in get_top_area_scores(
                    row["career_area_scores"]
                )
                if score > 0
            ]

            if top_areas:

                print(
                    "TOP AREAS   : "
                    + ", ".join(top_areas)
                )

            print_match_line(
                "TITLE EV",
                row["title_tech_matches"]
            )

            print_match_line(
                "GENERIC EV",
                row["generic_tech_matches"]
            )

            print_match_line(
                "NON-TECH EV",
                row["non_tech_matches"]
            )

            print("-" * 90)

    # --------------------------------------------------------
    # FINAL PROJECTED DISTRIBUTION
    # --------------------------------------------------------

    original_tech = sum(
        1
        for row in title_results
        if row["is_tech_role"] == "Tech"
    )

    original_non_tech = sum(
        1
        for row in title_results
        if row["is_tech_role"] == "Non-Tech"
    )

    projected_tech = (
        original_tech
        + result_counts.get("Tech", 0)
    )

    projected_non_tech = (
        original_non_tech
        + result_counts.get("Non-Tech", 0)
    )

    projected_ambiguous = (
        result_counts.get("Ambiguous", 0)
    )

    separator()

    print("PROJECTED FINAL DISTRIBUTION")
    print("=" * 90)

    total = len(title_results)

    for label, count in [
        ("Tech", projected_tech),
        ("Non-Tech", projected_non_tech),
        ("Ambiguous", projected_ambiguous)
    ]:

        pct = (
            count / total * 100
            if total
            else 0
        )

        print(
            f"{label:<15}"
            f"{count:>5} "
            f"({pct:>6.2f}%)"
        )

    separator()

    print(
        "DRY RUN COMPLETED - DATABASE NOT MODIFIED"
    )

    print("=" * 90)


if __name__ == "__main__":
    main()