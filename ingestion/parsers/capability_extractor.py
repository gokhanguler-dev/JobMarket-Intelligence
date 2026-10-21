import json
import re
from pathlib import Path

from ingestion.parsers.job_text_parser import clean_html_text


# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

TAXONOMY_PATH = (
    BASE_DIR
    / "config"
    / "capability_taxonomy.json"
)

CONTEXT_PATH = (
    BASE_DIR
    / "config"
    / "capability_context.json"
)


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_capability_taxonomy():
    data = load_json(TAXONOMY_PATH)
    return data["capabilities"]


def load_capability_context():
    data = load_json(CONTEXT_PATH)
    return data["capabilities"]


CAPABILITY_TAXONOMY = load_capability_taxonomy()
CAPABILITY_CONTEXT = load_capability_context()


# ------------------------------------------------------------
# TEXT
# ------------------------------------------------------------

def normalize_text(text):
    if not text:
        return ""

    text = clean_html_text(text)

    text = (
        text.replace("•", " ")
        .replace("●", " ")
        .replace("▪", " ")
        .replace("–", " ")
        .replace("—", " ")
    )

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ------------------------------------------------------------
# PATTERN MATCHING
# ------------------------------------------------------------

def pattern_matches(text, pattern):

    pattern = pattern.lower().strip()

    escaped_pattern = re.escape(pattern)

    regex = (
        rf"(?<!\w)"
        rf"{escaped_pattern}"
        rf"(?!\w)"
    )

    return (
        re.search(
            regex,
            text,
            flags=re.IGNORECASE
        )
        is not None
    )


def find_matching_patterns(text, patterns):

    matches = []

    for pattern in patterns:

        if pattern_matches(
            text,
            pattern
        ):
            matches.append(pattern)

    return matches


# ------------------------------------------------------------
# CONTEXT
# ------------------------------------------------------------

def get_context_config(capability_name):

    return CAPABILITY_CONTEXT.get(
        capability_name,
        {
            "career_areas": [],
            "roles": [],
        }
    )


def evaluate_context(
    capability_name,
    career_area=None,
    role_name=None,
):

    config = get_context_config(
        capability_name
    )

    relevant_areas = set(
        config.get(
            "career_areas",
            []
        )
    )

    relevant_roles = set(
        config.get(
            "roles",
            []
        )
    )

    area_match = (
        career_area in relevant_areas
        if career_area
        else False
    )

    role_match = (
        role_name in relevant_roles
        if role_name
        else False
    )

    return {
        "area_match": area_match,
        "role_match": role_match,
        "context_match": (
            area_match
            or role_match
        ),
    }


# ------------------------------------------------------------
# EXTRACTION
# ------------------------------------------------------------

def extract_capabilities(
    text,
    career_area=None,
    role_name=None,
):
    """
    Capability Taxonomy V1.1

    Acceptance rules:

    1. Strong evidence + valid context
       -> Strong Context

    2. Strong evidence without valid context
       -> rejected from production matches

    3. Medium evidence + valid context
       -> Contextual

    4. Medium evidence without context
       -> not accepted

    Context therefore protects against examples such as
    a DevOps job containing company boilerplate about
    building mobile applications.
    """

    normalized_text = normalize_text(text)

    if not normalized_text:
        return []

    results = []

    for capability in CAPABILITY_TAXONOMY:

        capability_name = capability["name"]

        strong_matches = find_matching_patterns(
            normalized_text,
            capability.get(
                "strong_patterns",
                []
            )
        )

        medium_matches = find_matching_patterns(
            normalized_text,
            capability.get(
                "medium_patterns",
                []
            )
        )

        context = evaluate_context(
            capability_name,
            career_area=career_area,
            role_name=role_name,
        )

        # --------------------------------------------
        # STRONG + CONTEXT
        # --------------------------------------------

        if (
            strong_matches
            and context["context_match"]
        ):

            results.append(
                {
                    "capability": capability_name,
                    "category": capability["category"],
                    "confidence": "Strong Context",
                    "evidence_type": "Strong",
                    "strong_matches": strong_matches,
                    "medium_matches": medium_matches,
                    "area_match": context["area_match"],
                    "role_match": context["role_match"],
                }
            )

            continue

        # --------------------------------------------
        # MEDIUM + CONTEXT
        # --------------------------------------------

        if (
            medium_matches
            and context["context_match"]
        ):

            results.append(
                {
                    "capability": capability_name,
                    "category": capability["category"],
                    "confidence": "Contextual",
                    "evidence_type": "Medium",
                    "strong_matches": strong_matches,
                    "medium_matches": medium_matches,
                    "area_match": context["area_match"],
                    "role_match": context["role_match"],
                }
            )

    return results


# ------------------------------------------------------------
# DIAGNOSTICS
# ------------------------------------------------------------

def extract_capability_candidates(
    text,
    career_area=None,
    role_name=None,
):
    """
    Returns evidence that was NOT accepted.

    Used only for QA/profiling.

    Reasons:
      STRONG_NO_CONTEXT
      MEDIUM_NO_CONTEXT
    """

    normalized_text = normalize_text(text)

    if not normalized_text:
        return []

    results = []

    for capability in CAPABILITY_TAXONOMY:

        capability_name = capability["name"]

        strong_matches = find_matching_patterns(
            normalized_text,
            capability.get(
                "strong_patterns",
                []
            )
        )

        medium_matches = find_matching_patterns(
            normalized_text,
            capability.get(
                "medium_patterns",
                []
            )
        )

        if (
            not strong_matches
            and not medium_matches
        ):
            continue

        context = evaluate_context(
            capability_name,
            career_area=career_area,
            role_name=role_name,
        )

        if context["context_match"]:
            continue

        if strong_matches:
            rejection_reason = (
                "STRONG_NO_CONTEXT"
            )
        else:
            rejection_reason = (
                "MEDIUM_NO_CONTEXT"
            )

        results.append(
            {
                "capability": capability_name,
                "category": capability["category"],
                "confidence": "Rejected Candidate",
                "rejection_reason": rejection_reason,
                "strong_matches": strong_matches,
                "medium_matches": medium_matches,
                "area_match": context["area_match"],
                "role_match": context["role_match"],
            }
        )

    return results