from collections import Counter, defaultdict

from ingestion.loaders.dwh_loader import get_connection
from ingestion.parsers.skill_extractor import (
    load_skill_taxonomy,
    contains_alias,
    extract_skills,
)


# ============================================================
# SKILL TAXONOMY V2 - CANDIDATE TECHNOLOGIES
#
# IMPORTANT:
# These technologies are discovery candidates only.
# Running this profiler DOES NOT modify:
#   - skill_taxonomy.json
#   - STG tables
#   - DWH tables
#
# Candidates will be evaluated using the actual Tech job market.
# ============================================================

CANDIDATE_TECHNOLOGIES = {

    # ========================================================
    # PROGRAMMING LANGUAGES / RUNTIMES
    # ========================================================

    ".NET": [
        ".net",
        "dotnet",
    ],

    "C#": [
        "c#",
        "c sharp",
    ],

    "C++": [
        "c++",
        "cpp",
    ],

    "JavaScript": [
        "javascript",
        "java script",
    ],

    "TypeScript": [
        "typescript",
        "type script",
    ],

    "Go": [
        "golang",
        "go language",
    ],

    "PHP": [
        "php",
    ],

    "Ruby": [
        "ruby",
    ],

    "Kotlin": [
        "kotlin",
    ],

    "Swift": [
        "swift",
    ],

    "Dart": [
        "dart",
    ],

    "ABAP": [
        "abap",
    ],


    # ========================================================
    # BACKEND / WEB FRAMEWORKS
    # ========================================================

    "Node.js": [
        "node.js",
        "nodejs",
        "node js",
    ],

    "Spring": [
        "spring",
        "spring boot",
    ],

    "Django": [
        "django",
    ],

    "Flask": [
        "flask",
    ],

    "FastAPI": [
        "fastapi",
        "fast api",
    ],

    "ASP.NET": [
        "asp.net",
        "asp net",
    ],


    # ========================================================
    # FRONTEND
    # ========================================================

    "React": [
        "react",
        "react.js",
        "reactjs",
    ],

    "Angular": [
        "angular",
        "angular.js",
        "angularjs",
    ],

    "Vue.js": [
        "vue",
        "vue.js",
        "vuejs",
    ],

    "Next.js": [
        "next.js",
        "nextjs",
        "next js",
    ],


    # ========================================================
    # MOBILE
    # ========================================================

    "Flutter": [
        "flutter",
    ],

    "React Native": [
        "react native",
    ],

    "Android": [
        "android",
    ],

    "iOS": [
        "ios",
    ],


    # ========================================================
    # DATABASES / SEARCH / CACHE
    # ========================================================

    "MySQL": [
        "mysql",
    ],

    "MongoDB": [
        "mongodb",
        "mongo db",
    ],

    "Redis": [
        "redis",
    ],

    "Elasticsearch": [
        "elasticsearch",
        "elastic search",
    ],

    "OpenSearch": [
        "opensearch",
        "open search",
    ],

    "Cassandra": [
        "cassandra",
    ],

    "DynamoDB": [
        "dynamodb",
        "dynamo db",
    ],

    "SQLite": [
        "sqlite",
    ],


    # ========================================================
    # DEVOPS / PLATFORM / INFRASTRUCTURE
    # ========================================================

    "Jenkins": [
        "jenkins",
    ],

    "GitHub Actions": [
        "github actions",
    ],

    "GitLab CI": [
        "gitlab ci",
        "gitlab ci/cd",
    ],

    "Argo CD": [
        "argo cd",
        "argocd",
    ],

    "Ansible": [
        "ansible",
    ],

    "Helm": [
        "helm",
    ],

    "Prometheus": [
        "prometheus",
    ],

    "Grafana": [
        "grafana",
    ],

    "OpenTelemetry": [
        "opentelemetry",
        "open telemetry",
    ],

    "Datadog": [
        "datadog",
    ],


    # ========================================================
    # MESSAGING / STREAMING
    # ========================================================

    "RabbitMQ": [
        "rabbitmq",
        "rabbit mq",
    ],

    "ActiveMQ": [
        "activemq",
        "active mq",
    ],

    "Flink": [
        "apache flink",
        "flink",
    ],


    # ========================================================
    # DATA / ANALYTICS
    # ========================================================

    "Tableau": [
        "tableau",
    ],

    "Looker": [
        "looker",
    ],

    "Qlik": [
        "qlik",
        "qlik sense",
        "qlikview",
    ],

    "Trino": [
        "trino",
    ],

    "Presto": [
        "presto",
    ],

    "Hive": [
        "apache hive",
        "hive",
    ],

    "Hadoop": [
        "apache hadoop",
        "hadoop",
    ],

    "Delta Lake": [
        "delta lake",
    ],

    "Iceberg": [
        "apache iceberg",
        "iceberg",
    ],

    "Fivetran": [
        "fivetran",
    ],

    "Informatica": [
        "informatica",
    ],


    # ========================================================
    # AI / MACHINE LEARNING
    # ========================================================

    "PyTorch": [
        "pytorch",
    ],

    "TensorFlow": [
        "tensorflow",
        "tensor flow",
    ],

    "scikit-learn": [
        "scikit-learn",
        "scikit learn",
        "sklearn",
    ],

    "Hugging Face": [
        "hugging face",
        "huggingface",
    ],

    "MLflow": [
        "mlflow",
    ],

    "OpenAI": [
        "openai",
    ],

    "LlamaIndex": [
        "llamaindex",
        "llama index",
    ],


    # ========================================================
    # ENTERPRISE APPLICATIONS
    # ========================================================

    "SAP": [
        "sap",
    ],

    "SAP HANA": [
        "sap hana",
        "hana",
    ],

    "SAP S/4HANA": [
        "s/4hana",
        "s4hana",
        "sap s/4hana",
        "sap s4hana",
    ],

    "Salesforce": [
        "salesforce",
    ],

    "ServiceNow": [
        "servicenow",
        "service now",
    ],

    "Microsoft Dynamics": [
        "microsoft dynamics",
        "dynamics 365",
        "dynamics crm",
    ],


    # ========================================================
    # API / ARCHITECTURE TECHNOLOGIES
    # ========================================================

    "GraphQL": [
        "graphql",
        "graph ql",
    ],

    "gRPC": [
        "grpc",
    ],


    # ========================================================
    # SECURITY / OBSERVABILITY
    # ========================================================

    "Cloudflare": [
        "cloudflare",
    ],

    "Splunk": [
        "splunk",
    ],

    "SonarQube": [
        "sonarqube",
        "sonar qube",
    ],
}


# ============================================================
# SQL
# ============================================================

SQL_QUERY = """
SELECT
     f.JobPostingKey
    ,f.JobTitle
    ,ca.CareerAreaName
    ,r.RoleName
    ,f.Seniority
    ,COALESCE(s.Description, '') AS Description
FROM dwh.FactJobPosting f

INNER JOIN dwh.DimCareerArea ca
    ON ca.CareerAreaKey = f.CareerAreaKey

INNER JOIN dwh.DimRole r
    ON r.RoleKey = f.RoleKey

OUTER APPLY
(
    SELECT TOP 1
        jp.Description
    FROM stg.JobPosting jp
    WHERE jp.SourceSystem = f.SourceSystem
      AND jp.SourceJobID = f.SourceJobID
    ORDER BY jp.ExtractedAt DESC
) s

WHERE f.IsTechRole = 'Tech'

ORDER BY
    f.JobPostingKey;
"""


# ============================================================
# HELPERS
# ============================================================

def normalize_text(value):
    """
    Convert nullable database values into clean strings.
    """

    if value is None:
        return ""

    return str(value).strip()


def load_jobs(connection):
    """
    Load the current canonical Tech job universe from the DWH.
    """

    cursor = connection.cursor()

    try:

        cursor.execute(SQL_QUERY)

        columns = [
            column[0]
            for column in cursor.description
        ]

        jobs = []

        for row in cursor.fetchall():

            jobs.append(
                dict(
                    zip(
                        columns,
                        row
                    )
                )
            )

        return jobs

    finally:

        cursor.close()


def get_current_taxonomy_aliases(taxonomy):
    """
    Return all aliases currently defined in skill_taxonomy.json.

    Aliases are normalized to lowercase so they can be compared
    with candidate aliases.
    """

    aliases = set()

    for skill_aliases in taxonomy.values():

        for alias in skill_aliases:

            aliases.add(
                alias.lower().strip()
            )

    return aliases


def candidate_exists_in_current_taxonomy(
    candidate_aliases,
    current_aliases
):
    """
    Determine whether at least one candidate alias already exists
    in the current taxonomy.

    This is informational only.
    """

    for alias in candidate_aliases:

        if alias.lower().strip() in current_aliases:
            return True

    return False


def detect_candidate(text, aliases):
    """
    Detect a candidate technology using the same boundary-aware
    alias matching logic used by the production skill extractor.
    """

    for alias in aliases:

        if contains_alias(
            text,
            alias
        ):
            return True

    return False


def print_header(title):
    """
    Print a readable console section header.
    """

    print()
    print("=" * 90)
    print(title)
    print("=" * 90)


# ============================================================
# MAIN PROFILING
# ============================================================

def main():

    # --------------------------------------------------------
    # Load existing production taxonomy
    # --------------------------------------------------------

    taxonomy = load_skill_taxonomy()

    current_aliases = (
        get_current_taxonomy_aliases(
            taxonomy
        )
    )

    # --------------------------------------------------------
    # Load canonical Tech jobs
    # --------------------------------------------------------

    connection = None

    try:

        connection = get_connection()

        jobs = load_jobs(
            connection
        )

    finally:

        if connection is not None:
            connection.close()

    # --------------------------------------------------------
    # Counters
    # --------------------------------------------------------

    total_jobs = len(jobs)

    jobs_with_existing_skills = 0
    jobs_without_existing_skills = 0

    existing_skill_frequency = Counter()

    career_area_total = Counter()
    career_area_with_skill = Counter()

    candidate_frequency = Counter()

    candidate_career_areas = defaultdict(
        Counter
    )

    candidate_roles = defaultdict(
        Counter
    )

    candidate_job_examples = defaultdict(
        list
    )

    # ========================================================
    # PROFILE EACH TECH JOB
    # ========================================================

    for job in jobs:

        title = normalize_text(
            job["JobTitle"]
        )

        description = normalize_text(
            job["Description"]
        )

        career_area = (
            normalize_text(
                job["CareerAreaName"]
            )
            or "Unknown"
        )

        role = (
            normalize_text(
                job["RoleName"]
            )
            or "Other"
        )

        # Use title + description because both contain
        # technology signals.
        text = (
            f"{title}\n"
            f"{description}"
        )

        career_area_total[
            career_area
        ] += 1

        # ----------------------------------------------------
        # CURRENT TAXONOMY COVERAGE
        # ----------------------------------------------------

        existing_skills = (
            extract_skills(
                text
            )
        )

        if existing_skills:

            jobs_with_existing_skills += 1

            career_area_with_skill[
                career_area
            ] += 1

        else:

            jobs_without_existing_skills += 1

        for skill in existing_skills:

            existing_skill_frequency[
                skill
            ] += 1

        # ----------------------------------------------------
        # V2 CANDIDATE DISCOVERY
        # ----------------------------------------------------

        for candidate, aliases in (
            CANDIDATE_TECHNOLOGIES.items()
        ):

            if not detect_candidate(
                text,
                aliases
            ):
                continue

            candidate_frequency[
                candidate
            ] += 1

            candidate_career_areas[
                candidate
            ][
                career_area
            ] += 1

            candidate_roles[
                candidate
            ][
                role
            ] += 1

            # Keep only a few examples to make console output
            # readable.
            if (
                len(
                    candidate_job_examples[
                        candidate
                    ]
                )
                < 3
            ):

                candidate_job_examples[
                    candidate
                ].append(
                    title
                )

    # ========================================================
    # GENERAL SUMMARY
    # ========================================================

    print_header(
        "SKILL TAXONOMY V2 PROFILER"
    )

    print(
        f"Tech jobs                 : "
        f"{total_jobs}"
    )

    print(
        f"Current taxonomy skills   : "
        f"{len(taxonomy)}"
    )

    print(
        f"Jobs with existing skills : "
        f"{jobs_with_existing_skills}"
    )

    print(
        f"Jobs without skills       : "
        f"{jobs_without_existing_skills}"
    )

    if total_jobs > 0:

        coverage = (
            jobs_with_existing_skills
            * 100.0
            / total_jobs
        )

    else:

        coverage = 0.0

    print(
        f"Existing coverage         : "
        f"{coverage:.2f}%"
    )

    # ========================================================
    # CAREER AREA COVERAGE
    # ========================================================

    print_header(
        "CURRENT TAXONOMY COVERAGE BY CAREER AREA"
    )

    for career_area, count in (
        career_area_total.most_common()
    ):

        covered = (
            career_area_with_skill[
                career_area
            ]
        )

        if count > 0:

            area_coverage = (
                covered
                * 100.0
                / count
            )

        else:

            area_coverage = 0.0

        print(
            f"{career_area:<32} "
            f"{covered:>4}/{count:<4} "
            f"{area_coverage:>7.2f}%"
        )

    # ========================================================
    # CURRENT TAXONOMY SKILL FREQUENCY
    # ========================================================

    print_header(
        "CURRENT TAXONOMY SKILL FREQUENCY"
    )

    if not existing_skill_frequency:

        print(
            "No existing skills detected."
        )

    else:

        for skill, count in (
            existing_skill_frequency.most_common()
        ):

            print(
                f"{skill:<30} : "
                f"{count:>4}"
            )

    # ========================================================
    # ALL OBSERVED V2 CANDIDATES
    # ========================================================

    print_header(
        "V2 TECHNOLOGY CANDIDATES"
    )

    if not candidate_frequency:

        print(
            "No candidate technologies detected."
        )

    else:

        for candidate, count in (
            candidate_frequency.most_common()
        ):

            already_present = (
                candidate_exists_in_current_taxonomy(
                    CANDIDATE_TECHNOLOGIES[
                        candidate
                    ],
                    current_aliases
                )
            )

            if already_present:
                status = "EXISTING"
            else:
                status = "NEW"

            print()

            print(
                f"{candidate:<25} "
                f"{count:>4} jobs "
                f"[{status}]"
            )

            # ----------------------------------------------
            # Top Career Areas
            # ----------------------------------------------

            top_areas = (
                candidate_career_areas[
                    candidate
                ].most_common(3)
            )

            if top_areas:

                print(
                    "  Career Areas : "
                    + ", ".join(
                        f"{name}={value}"
                        for name, value
                        in top_areas
                    )
                )

            # ----------------------------------------------
            # Top Roles
            # ----------------------------------------------

            top_roles = (
                candidate_roles[
                    candidate
                ].most_common(5)
            )

            if top_roles:

                print(
                    "  Roles        : "
                    + ", ".join(
                        f"{name}={value}"
                        for name, value
                        in top_roles
                    )
                )

            # ----------------------------------------------
            # Job examples
            # ----------------------------------------------

            examples = (
                candidate_job_examples[
                    candidate
                ]
            )

            if examples:

                print(
                    "  Examples     : "
                    + " | ".join(
                        examples
                    )
                )

    # ========================================================
    # NEW CANDIDATES ONLY
    # ========================================================

    print_header(
        "NEW CANDIDATES ONLY"
    )

    new_candidate_count = 0

    for candidate, count in (
        candidate_frequency.most_common()
    ):

        already_present = (
            candidate_exists_in_current_taxonomy(
                CANDIDATE_TECHNOLOGIES[
                    candidate
                ],
                current_aliases
            )
        )

        if already_present:
            continue

        new_candidate_count += 1

        print(
            f"{candidate:<25} : "
            f"{count:>4}"
        )

    print()

    print(
        f"Observed new candidates   : "
        f"{new_candidate_count}"
    )

    # ========================================================
    # JOBS WITH NO CURRENT SKILL COVERAGE
    # ========================================================

    print_header(
        "SAMPLE JOBS WITH NO CURRENT SKILL COVERAGE"
    )

    no_skill_examples = 0

    for job in jobs:

        title = normalize_text(
            job["JobTitle"]
        )

        description = normalize_text(
            job["Description"]
        )

        text = (
            f"{title}\n"
            f"{description}"
        )

        existing_skills = (
            extract_skills(
                text
            )
        )

        if existing_skills:
            continue

        print(
            f"{job['JobPostingKey']:>6} | "
            f"{normalize_text(job['CareerAreaName']):<30} | "
            f"{normalize_text(job['RoleName']):<25} | "
            f"{title}"
        )

        no_skill_examples += 1

        if no_skill_examples >= 30:
            break

    if no_skill_examples == 0:

        print(
            "Every Tech job has at least one "
            "existing taxonomy skill."
        )

    # ========================================================
    # COMPLETED
    # ========================================================

    print_header(
        "PROFILING COMPLETED"
    )

    print(
        "No database records or taxonomy files "
        "were modified."
    )


if __name__ == "__main__":
    main()