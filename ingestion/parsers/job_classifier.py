import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

ROLE_TAXONOMY_PATH = (
    BASE_DIR / "config" / "role_taxonomy.json"
)

SENIORITY_TAXONOMY_PATH = (
    BASE_DIR / "config" / "seniority_taxonomy.json"
)


def load_taxonomy(file_path):

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def contains_term(text, term):

    if not text:
        return False

    pattern = (
        r"(?<!\w)"
        + re.escape(term.lower())
        + r"(?!\w)"
    )

    return bool(
        re.search(pattern, text.lower())
    )


# ============================================================
# ROLE CLASSIFICATION
# ============================================================

def classify_role(job_title):

    if not job_title:
        return "Unknown"

    taxonomy = load_taxonomy(
        ROLE_TAXONOMY_PATH
    )

    for normalized_role, aliases in taxonomy.items():

        for alias in aliases:

            if contains_term(job_title, alias):
                return normalized_role

    return "Other"


# ============================================================
# SENIORITY CLASSIFICATION
# ============================================================

def classify_seniority(job_title):

    if not job_title:
        return "Unknown"

    taxonomy = load_taxonomy(
        SENIORITY_TAXONOMY_PATH
    )

    for seniority, aliases in taxonomy.items():

        for alias in aliases:

            if contains_term(job_title, alias):
                return seniority

    return "Unspecified"


# ============================================================
# COMPLETE JOB CLASSIFICATION
# ============================================================

def classify_job(job_title):

    return {
        "normalized_role": classify_role(job_title),
        "seniority": classify_seniority(job_title)
    }