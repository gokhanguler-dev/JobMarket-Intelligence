import os
import json
import time
from datetime import datetime
from pathlib import Path

import requests
from config.env_loader import load_project_env


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]


CONFIG_PATH = (
    BASE_DIR
    / "config"
    / "search_config.json"
)

RAW_DATA_DIR = (
    BASE_DIR
    / "data"
    / "raw"
)

RAW_DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_project_env(BASE_DIR)

API_KEY = os.getenv("JOOBLE_API_KEY")

BASE_URL = os.getenv(
    "JOOBLE_BASE_URL",
    "https://tr.jooble.org/api"
)

if not API_KEY:
    raise ValueError(
        "JOOBLE_API_KEY is not defined in environment"
    )


# ============================================================
# CONFIG
# ============================================================

def load_search_config():

    with open(
        CONFIG_PATH,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# HELPERS
# ============================================================

def sanitize_filename(value):

    value = value.lower().strip()

    value = value.replace(" ", "_")

    allowed_characters = (
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789_-"
    )

    return "".join(
        character
        for character in value
        if character in allowed_characters
    )


# ============================================================
# JOOBLE REQUEST
# ============================================================

def request_jobs(
    search_keyword,
    search_location,
    page,
    results_per_page
):

    url = f"{BASE_URL}/{API_KEY}"

    payload = {
        "keywords": search_keyword,
        "location": search_location,
        "page": page,
        "ResultOnPage": results_per_page
    }

    response = requests.post(
        url,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# SAVE RAW RESPONSE
# ============================================================

def save_raw_response(
    api_response,
    search_keyword,
    search_location,
    page,
    results_per_page
):

    extracted_at = datetime.now()

    raw_data = {

        "metadata": {
            "source_system": "Jooble",
            "search_keyword": search_keyword,
            "search_location": search_location,
            "page": page,
            "result_on_page": results_per_page,
            "extracted_at": extracted_at.isoformat()
        },

        "response": api_response
    }

    timestamp = extracted_at.strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    keyword_for_filename = (
        sanitize_filename(search_keyword)
    )

    output_file = (
        RAW_DATA_DIR
        / (
            f"jooble_"
            f"{keyword_for_filename}_"
            f"page_{page}_"
            f"{timestamp}.json"
        )
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            raw_data,
            file,
            ensure_ascii=False,
            indent=2
        )

    return output_file


# ============================================================
# COLLECT ONE QUERY
# ============================================================

def collect_query(
    search_keyword,
    search_location,
    results_per_page,
    max_pages
):

    print()
    print("=" * 70)
    print(f"QUERY : {search_keyword}")
    print("=" * 70)

    query_job_count = 0
    request_count = 0

    for page in range(
        1,
        max_pages + 1
    ):

        print()
        print(
            f"Requesting page {page}/{max_pages}..."
        )

        api_response = request_jobs(
            search_keyword=search_keyword,
            search_location=search_location,
            page=page,
            results_per_page=results_per_page
        )

        request_count += 1

        jobs = api_response.get(
            "jobs",
            []
        )

        total_count = api_response.get(
            "totalCount",
            0
        )

        output_file = save_raw_response(
            api_response=api_response,
            search_keyword=search_keyword,
            search_location=search_location,
            page=page,
            results_per_page=results_per_page
        )

        returned_count = len(jobs)

        query_job_count += returned_count

        print(
            f"Total available : {total_count}"
        )

        print(
            f"Jobs returned   : {returned_count}"
        )

        print(
            f"RAW file        : {output_file.name}"
        )

        # No more results available.
        if returned_count == 0:

            print(
                "No jobs returned. "
                "Pagination stopped."
            )

            break

        # If API returned fewer jobs than requested,
        # this is most likely the last page.
        if returned_count < results_per_page:

            print(
                "Last page reached."
            )

            break

        # Small pause between API requests.
        time.sleep(1)

    return {
        "requests": request_count,
        "jobs": query_job_count
    }


# ============================================================
# COLLECT ALL CONFIGURED QUERIES
# ============================================================

def collect_jobs():

    config = load_search_config()

    search_location = config.get(
        "location",
        "Türkiye"
    )

    # --------------------------------------------------------
    # CONFIG DEFAULTS
    # --------------------------------------------------------

    results_per_page = config.get(
        "results_per_page",
        10
    )

    max_pages = config.get(
        "max_pages_per_query",
        1
    )

    queries = config.get(
        "queries",
        []
    )

    # --------------------------------------------------------
    # ENVIRONMENT OVERRIDES
    #
    # Local/manual execution:
    #   Uses search_config.json values.
    #
    # Airflow execution:
    #   Can override these values using environment variables.
    # --------------------------------------------------------

    env_results_per_page = os.getenv(
        "JOOBLE_RESULTS_PER_PAGE"
    )

    env_max_pages = os.getenv(
        "JOOBLE_MAX_PAGES"
    )

    env_max_queries = os.getenv(
        "JOOBLE_MAX_QUERIES"
    )

    if env_results_per_page:

        results_per_page = int(
            env_results_per_page
        )

    if env_max_pages:

        max_pages = int(
            env_max_pages
        )

    if env_max_queries:

        max_queries = int(
            env_max_queries
        )

        queries = queries[:max_queries]

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not queries:

        raise ValueError(
            "No search queries defined "
            "in search_config.json"
        )

    if results_per_page <= 0:

        raise ValueError(
            "results_per_page must be greater than 0"
        )

    if max_pages <= 0:

        raise ValueError(
            "max_pages must be greater than 0"
        )

    # --------------------------------------------------------
    # RUN INFORMATION
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("JOOBLE JOB COLLECTOR")
    print("=" * 70)

    print(
        f"Location         : {search_location}"
    )

    print(
        f"Queries          : {len(queries)}"
    )

    print(
        f"Results per page : {results_per_page}"
    )

    print(
        f"Max pages/query  : {max_pages}"
    )

    print(
        f"Max API requests : "
        f"{len(queries) * max_pages}"
    )

    # --------------------------------------------------------
    # COLLECTION
    # --------------------------------------------------------

    total_requests = 0
    total_jobs = 0

    for search_keyword in queries:

        result = collect_query(
            search_keyword=search_keyword,
            search_location=search_location,
            results_per_page=results_per_page,
            max_pages=max_pages
        )

        total_requests += (
            result["requests"]
        )

        total_jobs += (
            result["jobs"]
        )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("COLLECTION COMPLETED")
    print("=" * 70)

    print(
        f"API requests : {total_requests}"
    )

    print(
        f"Jobs returned: {total_jobs}"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    collect_jobs()