import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"

ROLE_TAXONOMY_PATH = CONFIG_DIR / "role_taxonomy.json"
SENIORITY_TAXONOMY_PATH = CONFIG_DIR / "seniority_taxonomy.json"
NON_TECH_TAXONOMY_PATH = CONFIG_DIR / "non_tech_taxonomy.json"


def load_taxonomy(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


ROLE_TAXONOMY = load_taxonomy(ROLE_TAXONOMY_PATH)
SENIORITY_TAXONOMY = load_taxonomy(SENIORITY_TAXONOMY_PATH)
NON_TECH_TAXONOMY = load_taxonomy(NON_TECH_TAXONOMY_PATH)


def contains_term(text, term):
    if not text or not term:
        return False

    pattern = rf"(?<!\w){re.escape(term)}(?!\w)"

    return re.search(
        pattern,
        text,
        flags=re.IGNORECASE
    ) is not None


def find_role_match(job_title):
    matches = []

    for normalized_role, config in ROLE_TAXONOMY.items():
        career_area = config["career_area"]
        aliases = config["aliases"]

        for alias in aliases:
            if contains_term(job_title, alias):
                matches.append(
                    {
                        "normalized_role": normalized_role,
                        "career_area": career_area,
                        "matched_alias": alias,
                        "match_length": len(alias)
                    }
                )

    if not matches:
        return None

    matches.sort(
        key=lambda item: item["match_length"],
        reverse=True
    )

    return matches[0]


def find_non_tech_match(job_title):
    matches = []

    for category, aliases in NON_TECH_TAXONOMY.items():
        for alias in aliases:
            if contains_term(job_title, alias):
                matches.append(
                    {
                        "non_tech_category": category,
                        "matched_alias": alias,
                        "match_length": len(alias)
                    }
                )

    if not matches:
        return None

    matches.sort(
        key=lambda item: item["match_length"],
        reverse=True
    )

    return matches[0]


def classify_seniority(job_title):
    matches = []

    for seniority, aliases in SENIORITY_TAXONOMY.items():
        for alias in aliases:
            if contains_term(job_title, alias):
                matches.append(
                    {
                        "seniority": seniority,
                        "matched_alias": alias,
                        "match_length": len(alias)
                    }
                )

    if not matches:
        return "Unspecified"

    matches.sort(
        key=lambda item: item["match_length"],
        reverse=True
    )

    return matches[0]["seniority"]


def classify_job(job_title):
    tech_match = find_role_match(job_title)
    seniority = classify_seniority(job_title)

    # Strong tech rules have priority.
    # This prevents business-looking words inside a clearly technical
    # title from incorrectly pushing the job into Non-Tech.
    if tech_match:
        return {
            "is_tech_role": "Tech",
            "career_area": tech_match["career_area"],
            "normalized_role": tech_match["normalized_role"],
            "seniority": seniority,
            "matched_role_alias": tech_match["matched_alias"],
            "non_tech_category": None,
            "matched_non_tech_alias": None
        }

    non_tech_match = find_non_tech_match(job_title)

    if non_tech_match:
        return {
            "is_tech_role": "Non-Tech",
            "career_area": "Out of Scope",
            "normalized_role": "Out of Scope",
            "seniority": seniority,
            "matched_role_alias": None,
            "non_tech_category": non_tech_match["non_tech_category"],
            "matched_non_tech_alias": non_tech_match["matched_alias"]
        }

    return {
        "is_tech_role": "Ambiguous",
        "career_area": "Unknown",
        "normalized_role": "Other",
        "seniority": seniority,
        "matched_role_alias": None,
        "non_tech_category": None,
        "matched_non_tech_alias": None
    }