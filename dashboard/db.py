import os
from pathlib import Path

import pandas as pd
import pyodbc
from dotenv import load_dotenv


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv(ENV_PATH)

MSSQL_HOST = os.getenv(
    "MSSQL_HOST",
    "localhost"
)

MSSQL_PORT = os.getenv(
    "MSSQL_PORT",
    "1433"
)

MSSQL_DATABASE = os.getenv(
    "MSSQL_DATABASE",
    "JobMarketDWH"
)

MSSQL_USER = os.getenv(
    "MSSQL_USER",
    "sa"
)

MSSQL_PASSWORD = os.getenv(
    "MSSQL_SA_PASSWORD"
)

MSSQL_DRIVER = os.getenv(
    "MSSQL_DRIVER",
    "ODBC Driver 17 for SQL Server"
)


# ============================================================
# CONNECTION
# ============================================================

def get_connection():

    if not MSSQL_PASSWORD:
        raise ValueError(
            "MSSQL_SA_PASSWORD is not defined."
        )

    connection_string = (
        f"DRIVER={{{MSSQL_DRIVER}}};"
        f"SERVER={MSSQL_HOST},{MSSQL_PORT};"
        f"DATABASE={MSSQL_DATABASE};"
        f"UID={MSSQL_USER};"
        f"PWD={MSSQL_PASSWORD};"
        "TrustServerCertificate=yes;"
    )

    return pyodbc.connect(
        connection_string
    )


# ============================================================
# QUERY
# ============================================================

def run_query(query):

    connection = get_connection()

    try:

        dataframe = pd.read_sql_query(
            query,
            connection
        )

        return dataframe

    finally:

        connection.close()