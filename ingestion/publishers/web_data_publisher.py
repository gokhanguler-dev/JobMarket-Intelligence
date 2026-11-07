import json
import os
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import pyodbc
from config.env_loader import load_project_env
from ingestion.publishers.career_intelligence import OBSERVATION_QUERY, build_career_intelligence
from ingestion.publishers.role_opportunities import (
    load_latest_boards, load_opportunity_rows, summarize_opportunities,
)


# ---------------------------------------------------------
# PATHS / ENV
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_project_env(PROJECT_ROOT)

OUTPUT_DIR = PROJECT_ROOT / "web" / "public" / "data"

ISTANBUL_TZ = ZoneInfo("Europe/Istanbul")


# ---------------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------------

def get_connection():
    host = os.getenv("MSSQL_HOST", "localhost")
    port = os.getenv("MSSQL_PORT", "1433")
    database = os.getenv("MSSQL_DATABASE", "JobMarketDWH")
    user = os.getenv("MSSQL_USER", "sa")
    password = os.getenv("MSSQL_SA_PASSWORD")
    driver = os.getenv("MSSQL_DRIVER", "ODBC Driver 17 for SQL Server")

    if not password:
        raise RuntimeError("MSSQL_SA_PASSWORD is not defined.")

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={host},{port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"TrustServerCertificate=yes;"
    )

    return pyodbc.connect(connection_string)


# ---------------------------------------------------------
# JSON HELPERS
# ---------------------------------------------------------

def json_serializer(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    raise TypeError(
        f"Object of type {type(value).__name__} is not JSON serializable"
    )


def query_to_dicts(cursor, query):
    cursor.execute(query)

    columns = [column[0] for column in cursor.description]

    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def write_json(file_name, data):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = OUTPUT_DIR / file_name

    temporary_path = output_path.with_suffix(f".{uuid4().hex}.tmp")
    try:
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
                default=json_serializer,
            )
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    print(f"[OK] {file_name:<30} {len(data):>6} rows")


# ---------------------------------------------------------
# TIME / SCHEDULE HELPERS
# ---------------------------------------------------------

def utc_naive_to_istanbul(value):
    """
    SQL Server currently returns LastObservedAt as a timezone-naive value.
    The pipeline timestamp is interpreted as UTC and converted to Istanbul
    for the public serving metadata.
    """

    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(ISTANBUL_TZ)


def get_next_daily_run(now):
    """
    Daily multi-source pipeline:
    every day at 08:00 Europe/Istanbul.
    """

    candidate = datetime.combine(
        now.date(),
        time(hour=8),
        tzinfo=ISTANBUL_TZ,
    )

    if candidate <= now:
        candidate += timedelta(days=1)

    return candidate


def get_next_jooble_run(now):
    """
    Jooble pipeline:
    Tuesday + Friday at 09:00 Europe/Istanbul.
    """

    target_weekdays = {1, 4}  # Tuesday=1, Friday=4

    for days_ahead in range(0, 8):
        candidate_date = now.date() + timedelta(days=days_ahead)

        if candidate_date.weekday() not in target_weekdays:
            continue

        candidate = datetime.combine(
            candidate_date,
            time(hour=9),
            tzinfo=ISTANBUL_TZ,
        )

        if candidate > now:
            return candidate

    raise RuntimeError("Could not calculate next Jooble run.")


# ---------------------------------------------------------
# PUBLISH METADATA
# ---------------------------------------------------------

def publish_metadata(cursor):
    query = """
    SELECT
        COUNT(*) AS job_count,
        COUNT(DISTINCT CompanyKey) AS company_count,

        (
            SELECT COUNT(*)
            FROM dwh.DimSkill
        ) AS skill_count,

        (
            SELECT COUNT(*)
            FROM dwh.DimCapability
        ) AS capability_count,

        COUNT(DISTINCT SourceSystem) AS source_count,

        MAX(LastObservedAt) AS last_updated

    FROM dwh.FactJobPosting;
    """

    rows = query_to_dicts(cursor, query)

    if not rows:
        raise RuntimeError("Metadata query returned no rows.")

    row = rows[0]

    now = datetime.now(ISTANBUL_TZ)

    last_updated = utc_naive_to_istanbul(row["last_updated"])
    next_daily_run = get_next_daily_run(now)
    next_jooble_run = get_next_jooble_run(now)

    metadata = {
        "job_count": row["job_count"],
        "company_count": row["company_count"],
        "skill_count": row["skill_count"],
        "capability_count": row["capability_count"],
        "source_count": row["source_count"],

        "last_updated": (
            last_updated.isoformat()
            if last_updated
            else None
        ),

        "snapshot_generated_at": now.isoformat(),

        "pipeline_status": "Healthy",

        "daily_pipeline": {
            "name": "Daily Sources",
            "sources": [
                "Akbank",
                "Lever",
                "Greenhouse",
                "Workday",
                "SmartRecruiters",
                "Workable",
            ],
            "schedule": "Every day · 08:00",
            "next_run": next_daily_run.isoformat(),
        },

        "jooble_pipeline": {
            "name": "Jooble Refresh",
            "sources": ["Jooble"],
            "schedule": "Tuesday & Friday · 09:00",
            "next_run": next_jooble_run.isoformat(),
        },
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = OUTPUT_DIR / "metadata.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            metadata,
            file,
            ensure_ascii=False,
            indent=2,
            default=json_serializer,
        )

    print("[OK] metadata.json")


# ---------------------------------------------------------
# PUBLISH TECHNOLOGY DEMAND
# ---------------------------------------------------------

def publish_skill_demand(cursor):
    query = """
    SELECT *
    FROM marts.mart_skill_demand
    ORDER BY JobCount DESC, SkillName;
    """

    write_json(
        "skill-demand.json",
        query_to_dicts(cursor, query),
    )


# ---------------------------------------------------------
# PUBLISH ROLE × TECHNOLOGY DEMAND
# ---------------------------------------------------------

def publish_role_skill_demand(cursor):
    query = """
    SELECT *
    FROM marts.mart_role_skill_demand
    ORDER BY RoleName, JobCount DESC, SkillName;
    """

    write_json(
        "role-skill-demand.json",
        query_to_dicts(cursor, query),
    )


# ---------------------------------------------------------
# PUBLISH COMPANY TECHNOLOGY STACK
# ---------------------------------------------------------

def publish_company_tech_stack(cursor):
    query = """
    SELECT *
    FROM marts.mart_company_tech_stack
    ORDER BY CompanyName, JobCount DESC, SkillName;
    """

    write_json(
        "company-tech-stack.json",
        query_to_dicts(cursor, query),
    )


# ---------------------------------------------------------
# PUBLISH TECHNOLOGY STACK PAIRS
# ---------------------------------------------------------

def publish_technology_stack_pairs(cursor):
    query = """
    SELECT
        SkillKey1,
        SkillKey2,
        Skill1,
        Skill2,
        BothJobs,
        SupportPct,
        Confidence1To2Pct,
        Confidence2To1Pct,
        Lift
    FROM marts.mart_technology_stack_pairs
    ORDER BY BothJobs DESC, SkillKey1, SkillKey2;
    """

    write_json(
        "technology-stack-pairs.json",
        query_to_dicts(cursor, query),
    )


# ---------------------------------------------------------
# PUBLISH TECHNOLOGY TREND
# ---------------------------------------------------------

def publish_skill_trend(cursor):
    query = """
    SELECT *
    FROM marts.mart_skill_trend
    ORDER BY ObservationDate, JobCount DESC, SkillName;
    """

    write_json(
        "skill-trend.json",
        query_to_dicts(cursor, query),
    )


# ---------------------------------------------------------
# PUBLISH ROLE × SENIORITY × CAPABILITY DEMAND
# ---------------------------------------------------------

def publish_role_capability_demand(cursor):
    query = """
    SELECT
         CareerAreaName
        ,RoleName
        ,Seniority
        ,CapabilityCategory
        ,CapabilityName
        ,CapabilityJobCount
        ,CompanyCount
        ,SourceCount
        ,RoleSeniorityJobCount
        ,CapabilityDemandPercentage
    FROM marts.mart_role_capability_demand
    ORDER BY
         CapabilityDemandPercentage DESC
        ,CapabilityJobCount DESC
        ,CareerAreaName
        ,RoleName
        ,Seniority
        ,CapabilityName;
    """

    write_json(
        "role-capability-demand.json",
        query_to_dicts(cursor, query),
    )


# ---------------------------------------------------------
# PUBLISH SOURCE QUALITY
# ---------------------------------------------------------

def publish_career_intelligence(cursor):
    rows = query_to_dicts(cursor, OBSERVATION_QUERY)
    now = datetime.now(ISTANBUL_TZ)
    snapshot = build_career_intelligence(rows, now.date())
    boards = load_latest_boards(now)
    opportunity_rows = load_opportunity_rows(cursor, boards, now)
    snapshot["opportunities"] = summarize_opportunities(opportunity_rows, boards, now)
    write_json("career-intelligence.json", snapshot)


def publish_source_quality(cursor):
    query = """
    SELECT *
    FROM marts.mart_source_quality
    ORDER BY SourceSystem;
    """

    write_json(
        "source-quality.json",
        query_to_dicts(cursor, query),
    )


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():
    print("=" * 60)
    print("JOBMARKET WEB DATA PUBLISHER")
    print("=" * 60)

    print(f"Output directory: {OUTPUT_DIR}")
    print()

    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        print("[OK] SQL Server connection established.")
        print()

        # -------------------------------------------------
        # PUBLIC WEB DATASETS
        # -------------------------------------------------

        publish_metadata(cursor)

        publish_skill_demand(cursor)
        publish_role_skill_demand(cursor)

        publish_company_tech_stack(cursor)
        publish_technology_stack_pairs(cursor)

        publish_skill_trend(cursor)

        publish_role_capability_demand(cursor)

        publish_source_quality(cursor)
        publish_career_intelligence(cursor)

        print()
        print("=" * 60)
        print("WEB DATA PUBLISH COMPLETED")
        print("=" * 60)

    except Exception as exc:
        print()
        print("[ERROR] Web data publish failed.")
        print(exc)
        raise

    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()