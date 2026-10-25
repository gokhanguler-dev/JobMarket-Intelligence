import json
from pathlib import Path

from ingestion.loaders.dwh_loader import get_connection


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

TAXONOMY_FILE = (
    BASE_DIR
    / "config"
    / "capability_taxonomy.json"
)


# ============================================================
# SQL
# ============================================================

DELETE_QUERY = """
DELETE FROM stg.Capability;
"""


INSERT_QUERY = """
INSERT INTO stg.Capability
(
     CapabilityName
    ,CapabilityCategory
)
VALUES
(
    ?, ?
);
"""


# ============================================================
# LOAD TAXONOMY JSON
# ============================================================

def load_taxonomy():

    if not TAXONOMY_FILE.exists():

        raise FileNotFoundError(
            f"Capability taxonomy file not found: "
            f"{TAXONOMY_FILE}"
        )

    with open(
        TAXONOMY_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        taxonomy = json.load(file)

    return taxonomy


# ============================================================
# PARSE CAPABILITIES
# ============================================================

def parse_capabilities(taxonomy):

    capabilities = []

    # --------------------------------------------------------
    # Expected taxonomy structure:
    #
    # {
    #   "capabilities": [
    #       {
    #           "name": "...",
    #           "category": "...",
    #           ...
    #       }
    #   ]
    # }
    # --------------------------------------------------------

    taxonomy_capabilities = taxonomy.get(
        "capabilities",
        []
    )

    for capability in taxonomy_capabilities:

        capability_name = capability.get(
            "name"
        )

        capability_category = capability.get(
            "category"
        )

        if not capability_name:
            raise ValueError(
                "Capability without name found "
                "in capability taxonomy."
            )

        if not capability_category:
            raise ValueError(
                "Capability without category found: "
                f"{capability_name}"
            )

        capabilities.append(
            {
                "capability_name":
                    capability_name.strip(),

                "capability_category":
                    capability_category.strip(),
            }
        )

    return capabilities


# ============================================================
# VALIDATION
# ============================================================

def validate_capabilities(capabilities):

    if not capabilities:

        raise ValueError(
            "No capabilities found in taxonomy."
        )

    names = [
        row["capability_name"]
        for row in capabilities
    ]

    duplicate_names = sorted(
        {
            name
            for name in names
            if names.count(name) > 1
        }
    )

    if duplicate_names:

        raise ValueError(
            "Duplicate capability names found: "
            + ", ".join(duplicate_names)
        )

    categories = sorted(
        {
            row["capability_category"]
            for row in capabilities
        }
    )

    print()
    print("=" * 70)
    print(
        "CAPABILITY TAXONOMY VALIDATION"
    )
    print("=" * 70)

    print(
        f"Capabilities : "
        f"{len(capabilities)}"
    )

    print(
        f"Categories   : "
        f"{len(categories)}"
    )

    print()

    print("CATEGORY DISTRIBUTION")
    print("-" * 70)

    for category in categories:

        count = sum(
            1
            for row in capabilities
            if row["capability_category"]
            == category
        )

        print(
            f"{category:<30}: "
            f"{count}"
        )

    print("=" * 70)


# ============================================================
# LOAD STAGING
# ============================================================

def load_staging(
    cursor,
    capabilities
):

    # --------------------------------------------------------
    # Full refresh:
    # capability_taxonomy.json is the source-of-truth.
    # --------------------------------------------------------

    cursor.execute(
        DELETE_QUERY
    )

    parameters = [
        (
            row["capability_name"],
            row["capability_category"],
        )
        for row in capabilities
    ]

    cursor.fast_executemany = True

    cursor.executemany(
        INSERT_QUERY,
        parameters
    )


# ============================================================
# MAIN
# ============================================================

def run():

    connection = None
    cursor = None

    try:

        # ----------------------------------------------------
        # 1. READ TAXONOMY
        # ----------------------------------------------------

        taxonomy = load_taxonomy()

        # ----------------------------------------------------
        # 2. PARSE
        # ----------------------------------------------------

        capabilities = parse_capabilities(
            taxonomy
        )

        # ----------------------------------------------------
        # 3. VALIDATE
        # ----------------------------------------------------

        validate_capabilities(
            capabilities
        )

        # ----------------------------------------------------
        # 4. DATABASE CONNECTION
        # ----------------------------------------------------

        connection = get_connection()
        cursor = connection.cursor()

        # ----------------------------------------------------
        # 5. FULL REFRESH STAGING
        # ----------------------------------------------------

        load_staging(
            cursor,
            capabilities
        )

        connection.commit()

        # ----------------------------------------------------
        # 6. COMPLETE
        # ----------------------------------------------------

        print()
        print("=" * 70)
        print(
            "CAPABILITY TAXONOMY LOAD COMPLETED"
        )
        print("=" * 70)

        print(
            f"Rows loaded : "
            f"{len(capabilities)}"
        )

        print(
            "Target      : "
            "stg.Capability"
        )

        print(
            "Database changes committed."
        )

    except Exception as error:

        if connection is not None:
            connection.rollback()

        print()
        print("=" * 70)
        print(
            "CAPABILITY TAXONOMY LOAD FAILED"
        )
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
# CLI
# ============================================================

if __name__ == "__main__":

    run()