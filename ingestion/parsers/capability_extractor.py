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
            "context_scope": "role_sensitive",
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

    context_scope = config.get(
        "context_scope",
        "role_sensitive"
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
        "context_scope": context_scope,
    }


# ------------------------------------------------------------
# ACCEPTANCE
# ------------------------------------------------------------

def evaluate_acceptance(
    strong_matches,
    medium_matches,
    context,
):
    """
    Capability Taxonomy V1.2 acceptance rules.

    1. Strong evidence + role match
       -> Strong Role Context

    2. Strong evidence + area match
       + cross-functional capability
       -> Strong Area Context

    3. Medium evidence + role match
       -> Contextual Role

    4. All other evidence
       -> rejected from production matches

    Area match alone is intentionally insufficient
    for role-sensitive capabilities and for
    medium evidence.
    """

    # --------------------------------------------
    # STRONG + ROLE
    # --------------------------------------------

    if (
        strong_matches
        and context["role_match"]
    ):
        return {
            "accepted": True,
            "confidence": "Strong Role Context",
            "evidence_type": "Strong",
            "rejection_reason": None,
        }

    # --------------------------------------------
    # STRONG + AREA + CROSS-FUNCTIONAL
    # --------------------------------------------

    if (
        strong_matches
        and context["area_match"]
        and context["context_scope"] == "cross_functional"
    ):
        return {
            "accepted": True,
            "confidence": "Strong Area Context",
            "evidence_type": "Strong",
            "rejection_reason": None,
        }

    # --------------------------------------------
    # MEDIUM + ROLE
    # --------------------------------------------

    if (
        medium_matches
        and context["role_match"]
    ):
        return {
            "accepted": True,
            "confidence": "Contextual Role",
            "evidence_type": "Medium",
            "rejection_reason": None,
        }

    # --------------------------------------------
    # REJECTED STRONG EVIDENCE
    # --------------------------------------------

    if strong_matches:

        if (
            context["area_match"]
            and context["context_scope"] == "role_sensitive"
        ):
            rejection_reason = (
                "STRONG_AREA_ONLY_ROLE_SENSITIVE"
            )

        else:
            rejection_reason = (
                "STRONG_NO_VALID_CONTEXT"
            )

        return {
            "accepted": False,
            "confidence": None,
            "evidence_type": "Strong",
            "rejection_reason": rejection_reason,
        }

    # --------------------------------------------
    # REJECTED MEDIUM EVIDENCE
    # --------------------------------------------

    if medium_matches:

        if context["area_match"]:
            rejection_reason = (
                "MEDIUM_AREA_ONLY"
            )

        else:
            rejection_reason = (
                "MEDIUM_NO_VALID_CONTEXT"
            )

        return {
            "accepted": False,
            "confidence": None,
            "evidence_type": "Medium",
            "rejection_reason": rejection_reason,
        }

    # --------------------------------------------
    # NO EVIDENCE
    # --------------------------------------------

    return {
        "accepted": False,
        "confidence": None,
        "evidence_type": None,
        "rejection_reason": None,
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
    Capability Taxonomy V1.2

    Production extraction uses evidence strength,
    role context, career-area context and
    capability context scope.

    Accepted combinations:

    - Strong + Role Match
    - Strong + Area Match + Cross-Functional
    - Medium + Role Match

    Everything else is excluded from production
    capability matches.
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

        decision = evaluate_acceptance(
            strong_matches,
            medium_matches,
            context,
        )

        if not decision["accepted"]:
            continue

        results.append(
            {
                "capability": capability_name,
                "category": capability["category"],
                "confidence": decision["confidence"],
                "evidence_type": decision["evidence_type"],
                "strong_matches": strong_matches,
                "medium_matches": medium_matches,
                "area_match": context["area_match"],
                "role_match": context["role_match"],
                "context_scope": context["context_scope"],
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
    Returns capability evidence that was not
    accepted by the V1.2 production rules.

    Used only for QA/profiling.

    Possible rejection reasons:

    STRONG_AREA_ONLY_ROLE_SENSITIVE
    STRONG_NO_VALID_CONTEXT
    MEDIUM_AREA_ONLY
    MEDIUM_NO_VALID_CONTEXT
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

        decision = evaluate_acceptance(
            strong_matches,
            medium_matches,
            context,
        )

        if decision["accepted"]:
            continue

        if not decision["rejection_reason"]:
            continue

        results.append(
            {
                "capability": capability_name,
                "category": capability["category"],
                "confidence": "Rejected Candidate",
                "rejection_reason": decision["rejection_reason"],
                "strong_matches": strong_matches,
                "medium_matches": medium_matches,
                "area_match": context["area_match"],
                "role_match": context["role_match"],
                "context_scope": context["context_scope"],
            }
        )

    return results