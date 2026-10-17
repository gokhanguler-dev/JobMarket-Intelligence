from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
import pendulum


PROJECT_DIR = "/opt/airflow/jobmarket"
DBT_DIR = f"{PROJECT_DIR}/dbt/jobmarket"


default_args = {
    "owner": "gokhan",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


with DAG(
    dag_id="jobmarket_daily_pipeline",
    description="Daily JobMarket Intelligence ETL pipeline",
    default_args=default_args,
    start_date=pendulum.datetime(
        2026, 10, 17,
        tz="Europe/Istanbul"
    ),
    schedule="0 8 * * *",
    catchup=False,
    tags=["jobmarket", "etl", "dbt"],
) as dag:

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

    transform_staging = BashOperator(
        task_id="transform_staging",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m ingestion.loaders.stg_transform_loader"
        ),
    )

    load_dwh = BashOperator(
        task_id="load_dwh",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "python -m ingestion.loaders.dwh_loader"
        ),
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd {DBT_DIR} && "
            "dbt build "
            "--profiles-dir /opt/airflow/.dbt"
        ),
    )


    collect_akbank >> load_akbank_raw
    collect_lever >> load_lever_raw

    [
        load_akbank_raw,
        load_lever_raw,
    ] >> transform_staging

    transform_staging >> load_dwh >> dbt_build