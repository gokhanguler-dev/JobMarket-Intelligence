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
    dag_id="jobmarket_daily_pipeline",
    description="Daily JobMarket Intelligence ETL pipeline",
    default_args=default_args,
    start_date=pendulum.datetime(
        2026, 10, 17,
        tz="Europe/Istanbul",
    ),
    schedule="0 8,14,20 * * *",
    catchup=False,
    on_success_callback=notify_dag_success,
    on_failure_callback=notify_dag_failure,
    tags=[
        "jobmarket",
        "etl",
        "classification",
        "capability",
        "dbt",
        "publisher",
    ],
) as dag:

    # --------------------------------------------------------
    # 1. COLLECT SOURCES
    # --------------------------------------------------------

    collect_akbank = BashOperator(
        task_id="collect_akbank",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m ingestion.collectors.akbank_collector"
        ),
    )

    collect_lever = BashOperator(
        task_id="collect_lever",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m ingestion.collectors.lever_collector"
        ),
    )

    collect_greenhouse = BashOperator(
        task_id="collect_greenhouse",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m ingestion.collectors.greenhouse_collector"
        ),
    )

    collect_workday = BashOperator(
        task_id="collect_workday",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m ingestion.collectors.workday_collector"
        ),
    )

    collect_smartrecruiters = BashOperator(
        task_id="collect_smartrecruiters",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m ingestion.collectors.smartrecruiters_collector"
        ),
    )

    # --------------------------------------------------------
    # 2. LOAD RAW
    # --------------------------------------------------------

    load_akbank_raw = BashOperator(
        task_id="load_akbank_raw",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m ingestion.loaders.akbank_raw_loader"
        ),
    )

    load_lever_raw = BashOperator(
        task_id="load_lever_raw",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m ingestion.loaders.lever_raw_loader"
        ),
    )

    load_greenhouse_raw = BashOperator(
        task_id="load_greenhouse_raw",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m ingestion.loaders.greenhouse_raw_loader"
        ),
    )

    load_workday_raw = BashOperator(
        task_id="load_workday_raw",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m ingestion.loaders.workday_raw_loader"
        ),
    )

    load_smartrecruiters_raw = BashOperator(
        task_id="load_smartrecruiters_raw",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m ingestion.loaders.smartrecruiters_raw_loader"
        ),
    )

    # --------------------------------------------------------
    # 3. TRANSFORM STAGING
    # --------------------------------------------------------

    transform_staging = BashOperator(
        task_id="transform_staging",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m ingestion.loaders.stg_transform_loader"
        ),
    )

    # --------------------------------------------------------
    # 4. LOAD CORE DWH
    # --------------------------------------------------------

    load_dwh = BashOperator(
        task_id="load_dwh",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m ingestion.loaders.dwh_loader"
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

    collect_akbank >> load_akbank_raw
    collect_lever >> load_lever_raw
    collect_greenhouse >> load_greenhouse_raw
    collect_workday >> load_workday_raw
    collect_smartrecruiters >> load_smartrecruiters_raw

    [
        load_akbank_raw,
        load_lever_raw,
        load_greenhouse_raw,
        load_workday_raw,
        load_smartrecruiters_raw,
    ] >> transform_staging

    (
        transform_staging
        >> load_dwh
        >> classify_jobs
        >> load_capability_taxonomy
        >> extract_capabilities
        >> load_capability_dwh
        >> dbt_build
        >> publish_web_data
    )