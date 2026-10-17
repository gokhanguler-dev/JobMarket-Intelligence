import glob
import json
import os
from datetime import datetime

import pyodbc
from dotenv import load_dotenv


load_dotenv()

RAW_DIR = os.path.join("data", "raw")


def parse_datetime(value):
    if not value:
        return None

    # Python datetime ISO parser:
    # 2026-10-17T10:33:39.052109+00:00
    # 2026-10-16T23:45:53.660972
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def get_connection():
    connection_string = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={os.getenv('MSSQL_HOST')},{os.getenv('MSSQL_PORT')};"
        f"DATABASE={os.getenv('MSSQL_DATABASE')};"
        f"UID={os.getenv('MSSQL_USER')};"
        f"PWD={os.getenv('MSSQL_SA_PASSWORD')};"
        "TrustServerCertificate=yes;"
    )

    return pyodbc.connect(connection_string)


def main():
    files = glob.glob(os.path.join(RAW_DIR, "*.json"))

    conn = get_connection()
    cursor = conn.cursor()

    files_processed = 0
    raw_rows_updated = 0

    for file_path in files:
        file_name = os.path.basename(file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            metadata = payload.get("metadata", {})
            extracted_at_raw = metadata.get("extracted_at")

            if not extracted_at_raw:
                continue

            extracted_at = parse_datetime(extracted_at_raw)

            cursor.execute(
                """
                UPDATE stg.JobPostingRaw
                SET ExtractedAt = ?
                WHERE RawFileName = ?
                  AND ExtractedAt IS NULL
                """,
                extracted_at,
                file_name,
            )

            updated = cursor.rowcount

            if updated > 0:
                raw_rows_updated += updated

            files_processed += 1

        except Exception as exc:
            print(f"FAILED: {file_name} -> {exc}")

    # Processed STG inherits the exact extraction timestamp
    # from its corresponding RAW observation.
    cursor.execute(
        """
        UPDATE s
        SET s.ExtractedAt = r.ExtractedAt
        FROM stg.JobPosting s
        INNER JOIN stg.JobPostingRaw r
            ON r.RawJobPostingID = s.RawJobPostingID
        WHERE s.ExtractedAt IS NULL
          AND r.ExtractedAt IS NOT NULL
        """
    )

    stg_rows_updated = cursor.rowcount

    conn.commit()

    print()
    print(f"RAW files processed : {files_processed}")
    print(f"RAW rows updated    : {raw_rows_updated}")
    print(f"STG rows updated    : {stg_rows_updated}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()