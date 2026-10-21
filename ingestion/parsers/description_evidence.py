import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional


# ============================================================
# CONFIG
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG_PATH = (
    PROJECT_ROOT
    / "config"
    / "description_evidence.json"
)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    EVIDENCE_CONFIG = json.load(f)


CAREER_AREA_EVIDENCE = (
    EVIDENCE_CONFIG["career_area_evidence"]
)

TITLE_CAREER_AREA_EVIDENCE = (
    EVIDENCE_CONFIG["title_career_area_evidence"]
)

GENERIC_TECH_EVIDENCE = (
    EVIDENCE_CONFIG["generic_tech_evidence"]
)

TITLE_TECH_EVIDENCE = (
    EVIDENCE_CONFIG["title_tech_evidence"]
)

NON_TECH_EVIDENCE = (
    EVIDENCE_CONFIG["non_tech_evidence"]
)

SCORING = EVIDENCE_CONFIG["scoring"]


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_text(
    value: Optional[str]
) -> str:

    if not value:
        return ""

    text = str(value).lower()

    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = text.replace("’", "'")
    text = text.replace("“", '"')
    text = text.replace("”", '"')

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def contains_term(
    text: str,
    term: str
) -> bool:

    if not text or not term:
        return False

    text = normalize_text(text)
    term = normalize_text(term)

    pattern = (
        r"(?<![A-Za-z0-9_])"
        + re.escape(term)
        + r"(?![A-Za-z0-9_])"
    )

    return (
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )
        is not None
    )


# ============================================================
# GROUP MATCHING
# ============================================================

def find_group_matches(
    text: str,
    groups: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    """
    Each evidence group represents one semantic concept.

    Multiple aliases belonging to the same concept are counted
    only once.

    Example:

        large language model
        large language models
        llm
        llms

    -> one evidence group
    """

    text = normalize_text(text)

    matches = []

    for group in groups:

        group_name = group["name"]
        strength = group["strength"]

        matched_terms = []

        for term in group.get(
            "terms",
            []
        ):

            if contains_term(
                text,
                term
            ):

                matched_terms.append(
                    term
                )

        if matched_terms:

            matches.append(
                {
                    "group": group_name,
                    "strength": strength,
                    "matched_terms": matched_terms
                }
            )

    return matches


def score_group_matches(
    matches: List[Dict[str, Any]],
    strong_weight: int,
    medium_weight: int
) -> int:

    score = 0

    for match in matches:

        strength = match["strength"]

        if strength == "strong":

            score += strong_weight

        elif strength == "medium":

            score += medium_weight

    return score


# ============================================================
# DESCRIPTION CAREER AREA EVIDENCE
# ============================================================

def score_description_career_areas(
    description: str
) -> Dict[str, Dict[str, Any]]:

    results = {}

    for career_area, config in (
        CAREER_AREA_EVIDENCE.items()
    ):

        matches = find_group_matches(
            description,
            config.get(
                "groups",
                []
            )
        )

        score = score_group_matches(
            matches,
            strong_weight=SCORING[
                "description_strong_weight"
            ],
            medium_weight=SCORING[
                "description_medium_weight"
            ]
        )

        results[career_area] = {
            "score": score,
            "matches": matches
        }

    return results


# ============================================================
# TITLE CAREER AREA EVIDENCE
# ============================================================

def score_title_career_areas(
    title: str
) -> Dict[str, Dict[str, Any]]:

    """
    Career-area evidence extracted specifically from the title.

    This is separate from title_tech_evidence.

    Example:

        Solution Architect
            -> Tech evidence
            -> no forced career area

        Lead Business Analyst (ServiceNow)
            -> ServiceNow gives Enterprise Applications evidence

        Product Manager (Analytics)
            -> Analytics gives weak Data & Analytics evidence
            -> not enough by itself to force Tech
    """

    results = {}

    for career_area, config in (
        TITLE_CAREER_AREA_EVIDENCE.items()
    ):

        matches = find_group_matches(
            title,
            config.get(
                "groups",
                []
            )
        )

        score = score_group_matches(
            matches,
            strong_weight=SCORING[
                "title_career_strong_weight"
            ],
            medium_weight=SCORING[
                "title_career_medium_weight"
            ]
        )

        results[career_area] = {
            "score": score,
            "matches": matches
        }

    return results


# ============================================================
# GENERIC TECH EVIDENCE
# ============================================================

def score_generic_tech(
    description: str
) -> Dict[str, Any]:

    matches = find_group_matches(
        description,
        GENERIC_TECH_EVIDENCE.get(
            "groups",
            []
        )
    )

    score = score_group_matches(
        matches,
        strong_weight=SCORING[
            "generic_tech_strong_weight"
        ],
        medium_weight=SCORING[
            "generic_tech_medium_weight"
        ]
    )

    return {
        "score": score,
        "matches": matches
    }


# ============================================================
# TITLE TECH EVIDENCE
# ============================================================

def score_title_tech(
    title: str
) -> Dict[str, Any]:

    matches = find_group_matches(
        title,
        TITLE_TECH_EVIDENCE.get(
            "groups",
            []
        )
    )

    score = score_group_matches(
        matches,
        strong_weight=SCORING[
            "title_strong_weight"
        ],
        medium_weight=SCORING[
            "title_medium_weight"
        ]
    )

    return {
        "score": score,
        "matches": matches
    }


# ============================================================
# NON-TECH EVIDENCE
# ============================================================

def score_non_tech(
    description: str
) -> Dict[str, Any]:

    matches = find_group_matches(
        description,
        NON_TECH_EVIDENCE.get(
            "groups",
            []
        )
    )

    score = score_group_matches(
        matches,
        strong_weight=SCORING[
            "non_tech_strong_weight"
        ],
        medium_weight=SCORING[
            "non_tech_medium_weight"
        ]
    )

    return {
        "score": score,
        "matches": matches
    }


# ============================================================
# COMBINE CAREER AREA EVIDENCE
# ============================================================

def combine_career_area_scores(
    description_results:
        Dict[str, Dict[str, Any]],

    title_results:
        Dict[str, Dict[str, Any]]

) -> Dict[str, Dict[str, Any]]:

    """
    Combines title and description career-area evidence.

    Scores are additive because the evidence comes from two
    distinct locations:

        Title
        Description

    Evidence concepts remain deduplicated within each source.
    """

    combined = {}

    career_areas = set(
        description_results.keys()
    ) | set(
        title_results.keys()
    )

    for career_area in career_areas:

        description_result = (
            description_results.get(
                career_area,
                {
                    "score": 0,
                    "matches": []
                }
            )
        )

        title_result = (
            title_results.get(
                career_area,
                {
                    "score": 0,
                    "matches": []
                }
            )
        )

        combined[career_area] = {
            "score": (
                description_result["score"]
                + title_result["score"]
            ),

            "description_score":
                description_result["score"],

            "title_score":
                title_result["score"],

            "description_matches":
                description_result["matches"],

            "title_matches":
                title_result["matches"]
        }

    return combined


# ============================================================
# MAIN CLASSIFIER
# ============================================================

def classify_description(
    description: Optional[str],
    title: Optional[str] = None
) -> Dict[str, Any]:

    """
    V4.2 evidence classifier.

    Intended to run only after the V3 title taxonomy leaves
    a job as Ambiguous.

    Evidence layers:

        1. Title Tech Evidence
        2. Title Career-Area Evidence
        3. Description Career-Area Evidence
        4. Description Generic Tech Evidence
        5. Description Non-Tech Evidence

    Tech classification and Career Area classification are
    intentionally separate decisions.
    """

    description = normalize_text(
        description
    )

    title = normalize_text(
        title
    )

    # --------------------------------------------------------
    # EVIDENCE COLLECTION
    # --------------------------------------------------------

    description_career_results = (
        score_description_career_areas(
            description
        )
    )

    title_career_results = (
        score_title_career_areas(
            title
        )
    )

    combined_career_results = (
        combine_career_area_scores(
            description_results=(
                description_career_results
            ),
            title_results=(
                title_career_results
            )
        )
    )

    title_tech_result = (
        score_title_tech(
            title
        )
    )

    generic_tech_result = (
        score_generic_tech(
            description
        )
    )

    non_tech_result = (
        score_non_tech(
            description
        )
    )

    # --------------------------------------------------------
    # STRONGEST CAREER AREA
    # --------------------------------------------------------

    sorted_areas = sorted(
        combined_career_results.items(),
        key=lambda item:
            item[1]["score"],
        reverse=True
    )

    top_career_area = None
    top_career_area_score = 0

    if sorted_areas:

        top_career_area = (
            sorted_areas[0][0]
        )

        top_career_area_score = (
            sorted_areas[0][1]["score"]
        )

    # --------------------------------------------------------
    # TECH SCORE
    #
    # Important:
    #
    # We do NOT sum every career area.
    #
    # Only the strongest career-area evidence contributes to
    # the Tech score.
    #
    # This avoids descriptions listing many unrelated tools
    # from artificially inflating technical confidence.
    # --------------------------------------------------------

    title_tech_score = (
        title_tech_result["score"]
    )

    generic_tech_score = (
        generic_tech_result["score"]
    )

    tech_score = (
        title_tech_score
        + top_career_area_score
        + generic_tech_score
    )

    non_tech_score = (
        non_tech_result["score"]
    )

    margin = abs(
        tech_score
        - non_tech_score
    )

    # --------------------------------------------------------
    # THRESHOLDS
    # --------------------------------------------------------

    minimum_tech_score = (
        SCORING["minimum_tech_score"]
    )

    minimum_non_tech_score = (
        SCORING["minimum_non_tech_score"]
    )

    minimum_margin = (
        SCORING["minimum_score_margin"]
    )

    minimum_career_area_score = (
        SCORING[
            "minimum_career_area_score"
        ]
    )

    # --------------------------------------------------------
    # TECH / NON-TECH CLASSIFICATION
    # --------------------------------------------------------

    classification = "Ambiguous"

    if (
        tech_score
        >= minimum_tech_score

        and tech_score
        > non_tech_score

        and (
            tech_score
            - non_tech_score
        )
        >= minimum_margin
    ):

        classification = "Tech"

    elif (
        non_tech_score
        >= minimum_non_tech_score

        and non_tech_score
        > tech_score

        and (
            non_tech_score
            - tech_score
        )
        >= minimum_margin
    ):

        classification = "Non-Tech"

    # --------------------------------------------------------
    # CAREER AREA CLASSIFICATION
    # --------------------------------------------------------

    if classification == "Non-Tech":

        career_area = (
            "Out of Scope"
        )

    elif classification == "Tech":

        if (
            top_career_area_score
            >= minimum_career_area_score
        ):

            career_area = (
                top_career_area
            )

        else:

            career_area = (
                "Other Tech"
            )

    else:

        career_area = (
            "Unknown"
        )

    # --------------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------------

    if classification == "Ambiguous":

        confidence = "Low"

    elif margin >= 5:

        confidence = "High"

    else:

        confidence = "Medium"

    # --------------------------------------------------------
    # COMPATIBILITY OUTPUTS
    #
    # Keep these compatible with the existing V4.1 profiler.
    # --------------------------------------------------------

    career_area_scores = {
        area:
            result["score"]

        for area, result
        in combined_career_results.items()
    }

    career_area_matches = {}

    for area, result in (
        combined_career_results.items()
    ):

        matches = []

        for match in result[
            "title_matches"
        ]:

            copied_match = dict(
                match
            )

            copied_match["source"] = (
                "title"
            )

            matches.append(
                copied_match
            )

        for match in result[
            "description_matches"
        ]:

            copied_match = dict(
                match
            )

            copied_match["source"] = (
                "description"
            )

            matches.append(
                copied_match
            )

        if matches:

            career_area_matches[
                area
            ] = matches

    return {
        "classification":
            classification,

        "career_area":
            career_area,

        "tech_score":
            tech_score,

        "non_tech_score":
            non_tech_score,

        "margin":
            margin,

        "confidence":
            confidence,

        "title_tech_score":
            title_tech_score,

        "generic_tech_score":
            generic_tech_score,

        "top_career_area":
            top_career_area,

        "top_career_area_score":
            top_career_area_score,

        "career_area_scores":
            career_area_scores,

        "career_area_matches":
            career_area_matches,

        "title_tech_matches":
            title_tech_result["matches"],

        "generic_tech_matches":
            generic_tech_result["matches"],

        "non_tech_matches":
            non_tech_result["matches"],

        # V4.2-specific explainability fields

        "title_career_area_scores": {
            area:
                result["score"]

            for area, result
            in title_career_results.items()
        },

        "description_career_area_scores": {
            area:
                result["score"]

            for area, result
            in description_career_results.items()
        },

        "title_career_area_matches": {
            area:
                result["matches"]

            for area, result
            in title_career_results.items()

            if result["matches"]
        },

        "description_career_area_matches": {
            area:
                result["matches"]

            for area, result
            in description_career_results.items()

            if result["matches"]
        }
    }


# ============================================================
# DISPLAY HELPER
# ============================================================

def format_matches(
    matches: List[Dict[str, Any]]
) -> str:

    if not matches:
        return "-"

    parts = []

    for match in matches:

        group = match["group"]
        strength = match["strength"]

        terms = ", ".join(
            match["matched_terms"]
        )

        source = match.get(
            "source"
        )

        if source:

            parts.append(
                f"{group} "
                f"[{strength}/{source}] "
                f"({terms})"
            )

        else:

            parts.append(
                f"{group} "
                f"[{strength}] "
                f"({terms})"
            )

    return "; ".join(
        parts
    )


# ============================================================
# MANUAL SMOKE TEST
# ============================================================

if __name__ == "__main__":

    samples = [
        {
            "title":
                "Lead .NET AI Developer",

            "description":
                """
                We are looking for an experienced engineer
                to build software services using .NET,
                REST APIs and Git.

                The team also works with large language
                models.
                """
        },

        {
            "title":
                "Business Development Manager",

            "description":
                """
                You will own sales targets,
                generate pipeline,
                support business development initiatives
                and work with strategic customers.
                """
        },

        {
            "title":
                "Product Manager",

            "description":
                """
                You will work with multiple business
                stakeholders, define product priorities
                and coordinate delivery.
                """
        },

        {
            "title":
                "Lead Business Analyst (ServiceNow)",

            "description":
                """
                Work with business and technical teams
                to define requirements for enterprise
                workflow solutions.
                """
        },

        {
            "title":
                "Product Manager (Analytics)",

            "description":
                """
                Own product priorities, work with
                stakeholders and define roadmap.
                """
        },

        {
            "title":
                "Process Engineer",

            "description":
                """
                Improve manufacturing processes,
                production efficiency and operational
                performance.
                """
        }
    ]

    for sample in samples:

        result = classify_description(
            description=sample[
                "description"
            ],
            title=sample[
                "title"
            ]
        )

        print(
            "=" * 90
        )

        print(
            f"TITLE              : "
            f"{sample['title']}"
        )

        print(
            f"CLASSIFICATION     : "
            f"{result['classification']}"
        )

        print(
            f"CAREER AREA        : "
            f"{result['career_area']}"
        )

        print(
            f"TECH SCORE         : "
            f"{result['tech_score']}"
        )

        print(
            f"NON-TECH SCORE     : "
            f"{result['non_tech_score']}"
        )

        print(
            f"MARGIN             : "
            f"{result['margin']}"
        )

        print(
            f"CONFIDENCE         : "
            f"{result['confidence']}"
        )

        print(
            f"TITLE TECH SCORE   : "
            f"{result['title_tech_score']}"
        )

        print(
            f"GENERIC TECH SCORE : "
            f"{result['generic_tech_score']}"
        )

        print(
            f"TOP CAREER AREA    : "
            f"{result['top_career_area']} "
            f"("
            f"{result['top_career_area_score']}"
            f")"
        )

        print(
            "TITLE TECH MATCHES : "
            + format_matches(
                result[
                    "title_tech_matches"
                ]
            )
        )

        top_area = (
            result[
                "top_career_area"
            ]
        )

        title_area_matches = (
            result[
                "title_career_area_matches"
            ].get(
                top_area,
                []
            )
        )

        description_area_matches = (
            result[
                "description_career_area_matches"
            ].get(
                top_area,
                []
            )
        )

        print(
            "TITLE AREA MATCHES : "
            + format_matches(
                title_area_matches
            )
        )

        print(
            "DESC AREA MATCHES  : "
            + format_matches(
                description_area_matches
            )
        )

        print(
            "GENERIC MATCHES    : "
            + format_matches(
                result[
                    "generic_tech_matches"
                ]
            )
        )

        print(
            "NON-TECH MATCHES   : "
            + format_matches(
                result[
                    "non_tech_matches"
                ]
            )
        )