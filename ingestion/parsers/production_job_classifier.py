from typing import Optional, Dict, Any

from ingestion.parsers.job_classifier import classify_job
from ingestion.parsers.description_evidence import classify_description


CLASSIFICATION_VERSION = "V4.2"


def classify_job_production(
    job_title: Optional[str],
    description: Optional[str] = None
) -> Dict[str, Any]:

    """
    Production Job Classification Pipeline.

    Flow:
        1. Run deterministic title classifier V3.
        2. If V3 resolves Tech or Non-Tech, keep that result.
        3. If V3 returns Ambiguous, run V4.2 evidence classifier.
        4. If V4.2 resolves the job, use its classification.
        5. Otherwise preserve Ambiguous.

    Important:
        - V4.2 does NOT override confident V3 classifications.
        - Ambiguous is a valid final state.
        - ClassificationVersion records the production
          classifier version used for the result.
    """

    job_title = job_title or ""
    description = description or ""

    # ========================================================
    # STEP 1 - V3 TITLE CLASSIFIER
    # ========================================================

    v3_result = classify_job(
        job_title
    )

    v3_classification = (
        v3_result["is_tech_role"]
    )

    # ========================================================
    # STEP 2 - V3 ALREADY RESOLVED
    # ========================================================

    if v3_classification in (
        "Tech",
        "Non-Tech"
    ):

        return {
            "is_tech_role":
                v3_result["is_tech_role"],

            "career_area":
                v3_result["career_area"],

            "normalized_role":
                v3_result["normalized_role"],

            "seniority":
                v3_result["seniority"],

            "classification_confidence":
                "High",

            "classification_version":
                CLASSIFICATION_VERSION,

            "classification_stage":
                "V3 Title",

            "matched_role_alias":
                v3_result.get(
                    "matched_role_alias"
                ),

            "non_tech_category":
                v3_result.get(
                    "non_tech_category"
                ),

            "matched_non_tech_alias":
                v3_result.get(
                    "matched_non_tech_alias"
                ),

            "tech_score":
                None,

            "non_tech_score":
                None,

            "score_margin":
                None
        }

    # ========================================================
    # STEP 3 - V4.2 EVIDENCE CLASSIFIER
    # ========================================================

    evidence_result = classify_description(
        description=description,
        title=job_title
    )

    evidence_classification = (
        evidence_result["classification"]
    )

    # ========================================================
    # STEP 4 - V4.2 RESOLVED AS TECH
    # ========================================================

    if evidence_classification == "Tech":

        return {
            "is_tech_role":
                "Tech",

            "career_area":
                evidence_result[
                    "career_area"
                ],

            # V4.2 proves technical relevance / area,
            # but does not invent a normalized role.
            "normalized_role":
                v3_result[
                    "normalized_role"
                ],

            "seniority":
                v3_result["seniority"],

            "classification_confidence":
                evidence_result[
                    "confidence"
                ],

            "classification_version":
                CLASSIFICATION_VERSION,

            "classification_stage":
                "V4.2 Evidence",

            "matched_role_alias":
                None,

            "non_tech_category":
                None,

            "matched_non_tech_alias":
                None,

            "tech_score":
                evidence_result[
                    "tech_score"
                ],

            "non_tech_score":
                evidence_result[
                    "non_tech_score"
                ],

            "score_margin":
                evidence_result[
                    "margin"
                ]
        }

    # ========================================================
    # STEP 5 - V4.2 RESOLVED AS NON-TECH
    # ========================================================

    if evidence_classification == "Non-Tech":

        return {
            "is_tech_role":
                "Non-Tech",

            "career_area":
                "Out of Scope",

            "normalized_role":
                "Out of Scope",

            "seniority":
                v3_result["seniority"],

            "classification_confidence":
                evidence_result[
                    "confidence"
                ],

            "classification_version":
                CLASSIFICATION_VERSION,

            "classification_stage":
                "V4.2 Evidence",

            "matched_role_alias":
                None,

            "non_tech_category":
                "Evidence Classified",

            "matched_non_tech_alias":
                None,

            "tech_score":
                evidence_result[
                    "tech_score"
                ],

            "non_tech_score":
                evidence_result[
                    "non_tech_score"
                ],

            "score_margin":
                evidence_result[
                    "margin"
                ]
        }

    # ========================================================
    # STEP 6 - STILL AMBIGUOUS
    # ========================================================

    return {
        "is_tech_role":
            "Ambiguous",

        "career_area":
            "Unknown",

        "normalized_role":
            v3_result[
                "normalized_role"
            ],

        "seniority":
            v3_result["seniority"],

        "classification_confidence":
            "Low",

        "classification_version":
            CLASSIFICATION_VERSION,

        "classification_stage":
            "V4.2 Evidence",

        "matched_role_alias":
            None,

        "non_tech_category":
            None,

        "matched_non_tech_alias":
            None,

        "tech_score":
            evidence_result[
                "tech_score"
            ],

        "non_tech_score":
            evidence_result[
                "non_tech_score"
            ],

        "score_margin":
            evidence_result[
                "margin"
            ]
    }


if __name__ == "__main__":

    samples = [
        {
            "title":
                "Senior Data Engineer",

            "description":
                "Build scalable data pipelines."
        },
        {
            "title":
                "Marketing Manager",

            "description":
                "Execute marketing campaigns."
        },
        {
            "title":
                "Lead Business Analyst (ServiceNow)",

            "description":
                """
                Work with ServiceNow and enterprise
                workflow solutions.
                """
        },
        {
            "title":
                "Product Manager (Analytics)",

            "description":
                """
                Own product priorities and work with
                business stakeholders.
                """
        },
        {
            "title":
                "Process Engineer",

            "description":
                """
                Improve manufacturing processes and
                production efficiency.
                """
        }
    ]

    for sample in samples:

        result = classify_job_production(
            job_title=sample["title"],
            description=sample["description"]
        )

        print("=" * 80)
        print(
            f"TITLE       : "
            f"{sample['title']}"
        )
        print(
            f"CLASS       : "
            f"{result['is_tech_role']}"
        )
        print(
            f"AREA        : "
            f"{result['career_area']}"
        )
        print(
            f"ROLE        : "
            f"{result['normalized_role']}"
        )
        print(
            f"SENIORITY   : "
            f"{result['seniority']}"
        )
        print(
            f"CONFIDENCE  : "
            f"{result['classification_confidence']}"
        )
        print(
            f"VERSION     : "
            f"{result['classification_version']}"
        )
        print(
            f"STAGE       : "
            f"{result['classification_stage']}"
        )
        print(
            f"TECH SCORE  : "
            f"{result['tech_score']}"
        )
        print(
            f"NON-TECH    : "
            f"{result['non_tech_score']}"
        )