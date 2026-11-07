import json
import re
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

TAXONOMY_PATH = (
    BASE_DIR
    / "config"
    / "skill_taxonomy.json"
)


def load_skill_taxonomy():

    with open(
        TAXONOMY_PATH,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


@lru_cache(maxsize=2048)
def alias_pattern(alias):
    return re.compile(r"(?<!\w)" + re.escape(alias.lower()) + r"(?!\w)")


def contains_alias(text, alias):
    return bool(alias_pattern(alias).search(text.lower()))


def extract_skills(text, taxonomy=None):

    if not text:
        return []

    if taxonomy is None:
        taxonomy = load_skill_taxonomy()

    detected_skills = []

    for canonical_skill, aliases in taxonomy.items():

        for alias in aliases:

            if contains_alias(text, alias):

                detected_skills.append(
                    canonical_skill
                )

                break

    return detected_skills