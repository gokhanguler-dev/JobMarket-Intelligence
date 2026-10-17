import json
from pathlib import Path

from ingestion.parsers.job_text_parser import clean_html_text
from ingestion.parsers.skill_extractor import extract_skills


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = BASE_DIR / "data" / "raw"


# ============================================================
# FIND LATEST RAW FILE
# ============================================================

raw_files = list(
    RAW_DATA_DIR.glob("jooble_*.json")
)

if not raw_files:
    raise FileNotFoundError(
        "No Jooble RAW files found."
    )

latest_file = max(
    raw_files,
    key=lambda file: file.stat().st_mtime
)


# ============================================================
# READ RAW DATA
# ============================================================

with open(
    latest_file,
    "r",
    encoding="utf-8"
) as file:

    data = json.load(file)


metadata = data.get("metadata", {})
response_data = data.get("response", {})

jobs = response_data.get("jobs", [])


# ============================================================
# PROFILE SKILLS
# ============================================================

print()
print("=" * 80)
print("JOB SKILL PROFILING")
print("=" * 80)

print(f"RAW file : {latest_file.name}")
print(
    f"Keyword  : "
    f"{metadata.get('search_keyword')}"
)
print(
    f"Jobs     : "
    f"{len(jobs)}"
)

print()


for index, job in enumerate(
    jobs,
    start=1
):

    title = job.get("title") or ""

    snippet = clean_html_text(
        job.get("snippet")
    ) or ""

    # Search both title and snippet
    analysis_text = (
        f"{title} {snippet}"
    )

    skills = extract_skills(
        analysis_text
    )

    print("-" * 80)

    print(
        f"JOB {index}"
    )

    print(
        f"Title   : {title}"
    )

    print(
        f"Company : "
        f"{job.get('company')}"
    )

    print(
        f"Skills  : "
        f"{', '.join(skills) if skills else 'NONE'}"
    )

    print(
        f"Snippet : {snippet}"
    )


print()
print("=" * 80)
print("PROFILING COMPLETED")
print("=" * 80)