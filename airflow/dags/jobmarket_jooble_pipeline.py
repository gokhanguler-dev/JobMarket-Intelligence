from datetime import timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
import pendulum
from ingestion.notifications.email_notifier import (
    notify_dag_failure,
    notify_dag_success,
)


# ============================================================
# PATHS
# ============================================================

PROJECT_DIR = "/opt/airflow/jobmarket"
DBT_DIR = f"{PROJECT_DIR}/dbt/jobmarket"


# ============================================================
# DEFAULT ARGUMENTS
# ============================================================

default_args = {
    "owner": "gokhan",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


# ============================================================
# DAG
# ============================================================

with DAG(
    dag_id="jobmarket_jooble_pipeline",
    description=(
        "Quota-aware Jooble ingestion pipeline "
        "for JobMarket Intelligence"
    ),
    default_args=default_args,
    start_date=pendulum.datetime(
        2026, 10, 17,
        tz="Europe/Istanbul"
    ),
    schedule="0 9 * * 2,5",
    catchup=False,
    on_success_callback=notify_dag_success,
    on_failure_callback=notify_dag_failure,
    tags=[
        "jobmarket",
        "jooble",
        "etl",
        "classification",
        "capability",
        "dbt",
        "publisher",
    ],
) as dag:

    # --------------------------------------------------------
    # 1. COLLECT JOOBLE
    # --------------------------------------------------------

    collect_jooble = BashOperator(
        task_id="collect_jooble",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m "
            "ingestion.collectors.jooble_collector"
        ),
        env={
            "JOOBLE_MAX_PAGES": "1",
            "JOOBLE_MAX_QUERIES": "5",
            "JOOBLE_RESULTS_PER_PAGE": "10",
        },
        append_env=True,
    )


    # --------------------------------------------------------
    # 2. LOAD JOOBLE RAW
    # --------------------------------------------------------

    load_jooble_raw = BashOperator(
        task_id="load_jooble_raw",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m "
            "ingestion.loaders.jooble_raw_loader"
        ),
    )


    # --------------------------------------------------------
    # 3. TRANSFORM STAGING
    # --------------------------------------------------------

    transform_staging = BashOperator(
        task_id="transform_staging",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m "
            "ingestion.loaders.stg_transform_loader"
        ),
    )


    # --------------------------------------------------------
    # 4. LOAD CORE DWH
    # --------------------------------------------------------

    load_dwh = BashOperator(
        task_id="load_dwh",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m "
            "ingestion.loaders.dwh_loader"
        ),
    )


    # --------------------------------------------------------
    # 5. CLASSIFY JOBS
    # --------------------------------------------------------

    classify_jobs = BashOperator(
        task_id="classify_jobs",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m "
            "ingestion.loaders.job_classification_loader "
            "--apply"
        ),
    )


    # --------------------------------------------------------
    # 6. LOAD CAPABILITY TAXONOMY
    # --------------------------------------------------------

    load_capability_taxonomy = BashOperator(
        task_id="load_capability_taxonomy",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m "
            "ingestion.loaders.capability_taxonomy_loader"
        ),
    )


    # --------------------------------------------------------
    # 7. EXTRACT CAPABILITIES
    # --------------------------------------------------------

    extract_capabilities = BashOperator(
        task_id="extract_capabilities",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m "
            "ingestion.loaders.capability_staging_loader "
            "--apply"
        ),
    )


    # --------------------------------------------------------
    # 8. LOAD CAPABILITY DWH
    # --------------------------------------------------------

    load_capability_dwh = BashOperator(
        task_id="load_capability_dwh",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m "
            "ingestion.loaders.capability_dwh_loader"
        ),
    )


    # --------------------------------------------------------
    # 9. DBT BUILD
    # --------------------------------------------------------

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd {DBT_DIR} && "
            "dbt build "
            "--profiles-dir /opt/airflow/.dbt"
        ),
    )


    # --------------------------------------------------------
    # 10. PUBLISH WEB DATA
    # --------------------------------------------------------

    publish_web_data = BashOperator(
        task_id="publish_web_data",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m "
            "ingestion.publishers.web_data_publisher"
        ),
    )


    # --------------------------------------------------------
    # DEPENDENCIES
    # --------------------------------------------------------

    (
        collect_jooble
        >> load_jooble_raw
        >> transform_staging
        >> load_dwh
        >> classify_jobs
        >> load_capability_taxonomy
        >> extract_capabilities
        >> load_capability_dwh
        >> dbt_build
        >> publish_web_data
    )