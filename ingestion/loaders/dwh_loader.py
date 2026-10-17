import os
import re
from pathlib import Path

import pyodbc
from dotenv import load_dotenv


# ============================================================
# PATHS / ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / ".env"
DWH_SQL_DIR = BASE_DIR / "sql" / "dwh"

load_dotenv(ENV_PATH)


# ============================================================
# SQL SERVER CONFIGURATION
# ============================================================

SERVER = os.getenv("MSSQL_HOST", "localhost")
PORT = os.getenv("MSSQL_PORT", "1433")
DATABASE = os.getenv("MSSQL_DATABASE", "JobMarketDWH")
USERNAME = os.getenv("MSSQL_USER", "sa")
PASSWORD = os.getenv("MSSQL_SA_PASSWORD")

DRIVER = os.getenv(
    "MSSQL_DRIVER",
    "ODBC Driver 17 for SQL Server"
)


# ============================================================
# DWH LOAD SCRIPTS
# ============================================================

LOAD_SCRIPTS = [
    "09_load_dimensions.sql",
    "10_load_fact_job_posting.sql",
    "11_load_fact_job_observation.sql",
    "12_load_bridge_job_posting_skill.sql",
]


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    connection_string = (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVER},{PORT};"
        f"DATABASE={DATABASE};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD};"
        f"TrustServerCertificate=yes;"
    )

    return pyodbc.connect(
        connection_string,
        autocommit=False
    )


# ============================================================
# READ SQL FILE
# ============================================================

def read_sql_file(file_name):

    file_path = DWH_SQL_DIR / file_name

    if not file_path.exists():
        raise FileNotFoundError(
            f"SQL file not found: {file_path}"
        )

    return file_path.read_text(
        encoding="utf-8-sig"
    )


# ============================================================
# SPLIT SQL SERVER GO BATCHES
# ============================================================

def split_sql_batches(sql):

    batches = re.split(
        r"^\s*GO\s*;?\s*$",
        sql,
        flags=re.IGNORECASE | re.MULTILINE
    )

    return [
        batch.strip()
        for batch in batches
        if batch.strip()
    ]


# ============================================================
# CONSUME RESULT SETS
# ============================================================

def consume_result_sets(cursor):

    while True:

        try:
            has_next = cursor.nextset()

            if not has_next:
                break

        except pyodbc.ProgrammingError:
            break


# ============================================================
# EXECUTE SQL SCRIPT
# ============================================================

def execute_sql_script(cursor, file_name):

    sql = read_sql_file(file_name)

    batches = split_sql_batches(sql)

    print()
    print("=" * 70)
    print(f"RUNNING: {file_name}")
    print(f"BATCHES: {len(batches)}")
    print("=" * 70)

    for batch_number, batch in enumerate(
        batches,
        start=1
    ):

        cursor.execute(batch)

        consume_result_sets(cursor)

        print(
            f"  Batch {batch_number}/{len(batches)} completed"
        )

    print(f"COMPLETED: {file_name}")


# ============================================================
# LOAD DWH
# ============================================================

def load_dwh():

    connection = None
    cursor = None

    print()
    print("=" * 70)
    print("DWH LOAD STARTED")
    print("=" * 70)

    try:

        connection = get_connection()
        cursor = connection.cursor()

        for file_name in LOAD_SCRIPTS:

            execute_sql_script(
                cursor,
                file_name
            )

        connection.commit()

        print()
        print("=" * 70)
        print("DWH LOAD COMPLETED")
        print("=" * 70)
        print(
            f"Scripts executed : {len(LOAD_SCRIPTS)}"
        )

    except Exception as error:

        if connection is not None:
            connection.rollback()

        print()
        print("=" * 70)
        print("DWH LOAD FAILED")
        print("=" * 70)
        print("Transaction rolled back.")
        print(error)

        raise

    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    load_dwh()