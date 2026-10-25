from ingestion.loaders.dwh_loader import (
    get_connection,
    execute_sql_script,
)


# ============================================================
# CAPABILITY DWH LOAD SCRIPTS
# ============================================================

CAPABILITY_LOAD_SCRIPTS = [
    "15_load_dim_capability.sql",
    "16_load_bridge_job_posting_capability.sql",
]


# ============================================================
# LOAD CAPABILITY DWH
# ============================================================

def load_capability_dwh():

    connection = None
    cursor = None

    print()
    print("=" * 70)
    print("CAPABILITY DWH LOAD STARTED")
    print("=" * 70)

    try:

        connection = get_connection()
        cursor = connection.cursor()

        for file_name in CAPABILITY_LOAD_SCRIPTS:

            execute_sql_script(
                cursor,
                file_name
            )

        connection.commit()

        print()
        print("=" * 70)
        print("CAPABILITY DWH LOAD COMPLETED")
        print("=" * 70)

        print(
            f"Scripts executed : "
            f"{len(CAPABILITY_LOAD_SCRIPTS)}"
        )

    except Exception as error:

        if connection is not None:
            connection.rollback()

        print()
        print("=" * 70)
        print("CAPABILITY DWH LOAD FAILED")
        print("=" * 70)

        print(
            "Transaction rolled back."
        )

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

    load_capability_dwh()