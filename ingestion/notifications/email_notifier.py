import html
import os
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage

import pendulum
import pyodbc


ISTANBUL_TZ = "Europe/Istanbul"

PIPELINE_NAMES = {
    "jobmarket_daily_pipeline": "Daily Multi-Source Pipeline",
    "jobmarket_jooble_pipeline": "Jooble Pipeline",
}

SOURCE_TASKS = {
    "collect_akbank": "Akbank",
    "collect_lever": "Lever",
    "collect_greenhouse": "Greenhouse",
    "collect_workday": "Workday",
    "collect_smartrecruiters": "SmartRecruiters",
    "collect_workable": "Workable",
    "collect_jooble": "Jooble",
}

PIPELINE_TASKS = {
    "transform_staging": "Staging Transform",
    "load_dwh": "DWH Load",
    "classify_jobs": "Job Classification",
    "load_capability_taxonomy": "Capability Taxonomy",
    "extract_capabilities": "Capability Extraction",
    "load_capability_dwh": "Capability DWH Load",
    "dbt_build": "dbt Build",
    "publish_web_data": "Web Publisher",
}


def _get_env(name, default=None):
    value = os.getenv(name, default)

    if value is None or str(value).strip() == "":
        raise RuntimeError(
            f"Required environment variable is missing: {name}"
        )

    return value


def _to_istanbul(value):
    if value is None:
        return None

    return pendulum.instance(value).in_timezone(ISTANBUL_TZ)


def _format_datetime(value):
    value = _to_istanbul(value)

    if value is None:
        return "-"

    return value.format("DD MMM YYYY HH:mm:ss")


def _format_duration(start_date, end_date):
    if not start_date:
        return "-"

    end_date = end_date or datetime.utcnow()

    total_seconds = max(
        0,
        int((end_date - start_date).total_seconds()),
    )

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes}m {seconds}s"

    if minutes:
        return f"{minutes}m {seconds}s"

    return f"{seconds}s"


def _normalize_run_type(dag_run):
    run_type = getattr(dag_run, "run_type", None)

    if run_type is None:
        return "Unknown"

    value = getattr(run_type, "value", str(run_type))
    value = str(value).lower()

    if "manual" in value:
        return "Manual"

    if "scheduled" in value:
        return "Scheduled"

    if "backfill" in value:
        return "Backfill"

    return value.replace("_", " ").title()


def _state_symbol(state):
    state = str(state or "unknown").lower()

    if state == "success":
        return "✓"

    if state in {"failed", "upstream_failed"}:
        return "✗"

    if state == "skipped":
        return "○"

    if state in {"running", "queued", "scheduled"}:
        return "…"

    return "-"


def _get_task_states(dag_run):
    result = {}

    try:
        for task_instance in dag_run.get_task_instances():
            result[task_instance.task_id] = (
                str(task_instance.state or "unknown").lower()
            )
    except Exception as exc:
        print(
            "[Career Radar] Could not read task states: "
            f"{exc}"
        )

    return result


def _get_failed_tasks(task_states):
    return [
        task_id
        for task_id, state in task_states.items()
        if state in {"failed", "upstream_failed"}
    ]


def _get_market_snapshot():
    snapshot = {
        "Canonical Jobs": None,
        "Job Observations": None,
        "Technologies": None,
        "Capabilities": None,
        "Job-Skill Relationships": None,
        "Job-Capability Relationships": None,
    }

    connection = None

    queries = {
        "Canonical Jobs":
            "SELECT COUNT(*) FROM dwh.FactJobPosting",
        "Job Observations":
            "SELECT COUNT(*) FROM dwh.FactJobObservation",
        "Technologies":
            "SELECT COUNT(*) FROM dwh.DimSkill",
        "Capabilities":
            "SELECT COUNT(*) FROM dwh.DimCapability",
        "Job-Skill Relationships":
            "SELECT COUNT(*) FROM dwh.BridgeJobPostingSkill",
        "Job-Capability Relationships":
            "SELECT COUNT(*) FROM dwh.BridgeJobPostingCapability",
    }

    try:
        driver = _get_env(
            "MSSQL_DRIVER",
            "ODBC Driver 17 for SQL Server",
        )

        connection_string = (
            f"DRIVER={{{driver}}};"
            f"SERVER={_get_env('MSSQL_HOST')},"
            f"{_get_env('MSSQL_PORT', '1433')};"
            f"DATABASE={_get_env('MSSQL_DATABASE')};"
            f"UID={_get_env('MSSQL_USER')};"
            f"PWD={_get_env('MSSQL_SA_PASSWORD')};"
            "TrustServerCertificate=yes;"
            "Encrypt=no;"
        )

        connection = pyodbc.connect(
            connection_string,
            timeout=10,
        )

        cursor = connection.cursor()

        for label, query in queries.items():
            cursor.execute(query)
            row = cursor.fetchone()

            if row:
                snapshot[label] = int(row[0])

    except Exception as exc:
        print(
            "[Career Radar] Market snapshot could not be read: "
            f"{exc}"
        )

    finally:
        if connection is not None:
            connection.close()

    return snapshot


def _format_snapshot_value(value):
    if value is None:
        return "Unavailable"

    return f"{value:,}"


def _build_text_body(
    status,
    pipeline_name,
    run_type,
    dag_run,
    task_states,
    snapshot,
    error_summary,
):
    lines = [
        "CAREER RADAR — PRODUCTION RUN REPORT",
        "",
        f"Status: {status}",
        f"Pipeline: {pipeline_name}",
        f"Run Type: {run_type}",
        f"Started: {_format_datetime(dag_run.start_date)}",
        f"Finished: {_format_datetime(dag_run.end_date)}",
        (
            "Duration: "
            f"{_format_duration(dag_run.start_date, dag_run.end_date)}"
        ),
        f"Run ID: {dag_run.run_id}",
        "",
        "SOURCE STATUS",
    ]

    source_found = False

    for task_id, source_name in SOURCE_TASKS.items():
        if task_id in task_states:
            source_found = True
            state = task_states[task_id]

            lines.append(
                f"{_state_symbol(state)} "
                f"{source_name}: {state.upper()}"
            )

    if not source_found:
        lines.append("- No source tasks found")

    lines.extend([
        "",
        "PIPELINE STATUS",
    ])

    for task_id, label in PIPELINE_TASKS.items():
        if task_id in task_states:
            state = task_states[task_id]

            lines.append(
                f"{_state_symbol(state)} "
                f"{label}: {state.upper()}"
            )

    if status == "FAILED":
        failed_tasks = _get_failed_tasks(task_states)

        lines.extend([
            "",
            "FAILURE DETAILS",
            (
                "Failed Tasks: "
                + (
                    ", ".join(failed_tasks)
                    if failed_tasks
                    else "Unknown"
                )
            ),
            f"Error Summary: {error_summary or 'Not available'}",
        ])

    lines.extend([
        "",
        "CURRENT MARKET SNAPSHOT",
    ])

    for label, value in snapshot.items():
        lines.append(
            f"{label}: {_format_snapshot_value(value)}"
        )

    website = os.getenv(
        "CAREER_RADAR_URL",
        "https://techcareerradar.com",
    )

    lines.extend([
        "",
        "Career Radar",
        website,
        "",
        "Generated automatically by Career Radar.",
    ])

    return "\n".join(lines)


def _build_html_body(
    status,
    pipeline_name,
    run_type,
    dag_run,
    task_states,
    snapshot,
    error_summary,
):
    success = status == "SUCCESS"
    status_color = "#22c55e" if success else "#ef4444"
    website = os.getenv(
        "CAREER_RADAR_URL",
        "https://techcareerradar.com",
    )

    source_rows = ""

    for task_id, source_name in SOURCE_TASKS.items():
        if task_id not in task_states:
            continue

        state = task_states[task_id]

        source_rows += f"""
        <tr>
          <td>{html.escape(source_name)}</td>
          <td>
            {_state_symbol(state)}
            {html.escape(state.upper())}
          </td>
        </tr>
        """

    pipeline_rows = ""

    for task_id, label in PIPELINE_TASKS.items():
        if task_id not in task_states:
            continue

        state = task_states[task_id]

        pipeline_rows += f"""
        <tr>
          <td>{html.escape(label)}</td>
          <td>
            {_state_symbol(state)}
            {html.escape(state.upper())}
          </td>
        </tr>
        """

    snapshot_rows = ""

    for label, value in snapshot.items():
        snapshot_rows += f"""
        <tr>
          <td>{html.escape(label)}</td>
          <td>
            <strong>
              {html.escape(_format_snapshot_value(value))}
            </strong>
          </td>
        </tr>
        """

    failure_section = ""

    if not success:
        failed_tasks = _get_failed_tasks(task_states)
        failed_text = (
            ", ".join(failed_tasks)
            if failed_tasks
            else "Unknown"
        )

        failure_section = f"""
        <h3 style="margin-top:28px;">Failure Details</h3>
        <div style="
            background:#2a1518;
            border:1px solid #7f1d1d;
            padding:16px;
            border-radius:8px;
        ">
          <p>
            <strong>Failed Tasks:</strong>
            {html.escape(failed_text)}
          </p>
          <p>
            <strong>Error Summary:</strong>
            {html.escape(error_summary or "Not available")}
          </p>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <body style="
        margin:0;
        padding:0;
        background:#08111f;
        font-family:Arial,Helvetica,sans-serif;
        color:#e5e7eb;
    ">
      <div style="
          max-width:720px;
          margin:0 auto;
          padding:32px 18px;
      ">
        <div style="
            background:#0f1b2d;
            border:1px solid #203047;
            border-radius:14px;
            padding:28px;
        ">
          <div style="
              color:#22d3ee;
              font-size:13px;
              font-weight:bold;
              letter-spacing:1.5px;
          ">
            CAREER RADAR
          </div>

          <h1 style="
              margin:8px 0 4px;
              font-size:25px;
              color:#ffffff;
          ">
            Production Run Report
          </h1>

          <p style="
              color:{status_color};
              font-size:18px;
              font-weight:bold;
          ">
            {status}
          </p>

          <table style="
              width:100%;
              border-collapse:collapse;
              margin-top:20px;
          ">
            <tr>
              <td>Pipeline</td>
              <td><strong>{html.escape(pipeline_name)}</strong></td>
            </tr>
            <tr>
              <td>Run Type</td>
              <td>{html.escape(run_type)}</td>
            </tr>
            <tr>
              <td>Started</td>
              <td>{html.escape(_format_datetime(dag_run.start_date))}</td>
            </tr>
            <tr>
              <td>Finished</td>
              <td>{html.escape(_format_datetime(dag_run.end_date))}</td>
            </tr>
            <tr>
              <td>Duration</td>
              <td>
                {html.escape(
                    _format_duration(
                        dag_run.start_date,
                        dag_run.end_date,
                    )
                )}
              </td>
            </tr>
            <tr>
              <td>Run ID</td>
              <td>{html.escape(str(dag_run.run_id))}</td>
            </tr>
          </table>

          <h3 style="margin-top:28px;">Source Status</h3>
          <table style="
              width:100%;
              border-collapse:collapse;
          ">
            {source_rows}
          </table>

          <h3 style="margin-top:28px;">Pipeline Status</h3>
          <table style="
              width:100%;
              border-collapse:collapse;
          ">
            {pipeline_rows}
          </table>

          {failure_section}

          <h3 style="margin-top:28px;">Current Market Snapshot</h3>
          <table style="
              width:100%;
              border-collapse:collapse;
          ">
            {snapshot_rows}
          </table>

          <div style="
              margin-top:30px;
              padding-top:20px;
              border-top:1px solid #203047;
          ">
            <a
              href="{html.escape(website)}"
              style="
                  display:inline-block;
                  background:#0891b2;
                  color:#ffffff;
                  text-decoration:none;
                  padding:11px 18px;
                  border-radius:7px;
                  font-weight:bold;
              "
            >
              Open Career Radar
            </a>

            <p style="
                margin-top:20px;
                color:#94a3b8;
                font-size:12px;
            ">
              Generated automatically by Career Radar.
            </p>
          </div>
        </div>
      </div>
    </body>
    </html>
    """


def _send_email(subject, text_body, html_body):
    smtp_host = _get_env("SMTP_HOST")
    smtp_port = int(_get_env("SMTP_PORT", "587"))
    smtp_user = _get_env("SMTP_USER")
    smtp_password = _get_env("SMTP_PASSWORD")
    mail_from = _get_env("SMTP_MAIL_FROM")
    mail_to = _get_env("SMTP_MAIL_TO")

    recipients = [
        address.strip()
        for address in mail_to.split(",")
        if address.strip()
    ]

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = mail_from
    message["To"] = ", ".join(recipients)

    message.set_content(text_body)
    message.add_alternative(
        html_body,
        subtype="html",
    )

    ssl_context = ssl.create_default_context()

    with smtplib.SMTP(
        smtp_host,
        smtp_port,
        timeout=30,
    ) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ssl_context)
        smtp.ehlo()
        smtp.login(
            smtp_user,
            smtp_password,
        )
        smtp.send_message(message)


def _notify(context, status):
    try:
        dag_run = context.get("dag_run")

        if dag_run is None:
            print(
                "[Career Radar] Notification skipped: "
                "dag_run is unavailable."
            )
            return

        dag_id = dag_run.dag_id
        pipeline_name = PIPELINE_NAMES.get(
            dag_id,
            dag_id,
        )

        run_type = _normalize_run_type(dag_run)
        task_states = _get_task_states(dag_run)
        snapshot = _get_market_snapshot()

        error = context.get("exception")
        reason = context.get("reason")

        error_summary = None

        if error:
            error_summary = str(error)
        elif reason:
            error_summary = str(reason)

        subject_time = (
            _to_istanbul(
                dag_run.end_date
                or dag_run.start_date
            )
            or pendulum.now(ISTANBUL_TZ)
        )

        subject = (
            f"[Career Radar] {status} — "
            f"{pipeline_name} — "
            f"{subject_time.format('DD MMM YYYY HH:mm')}"
        )

        text_body = _build_text_body(
            status=status,
            pipeline_name=pipeline_name,
            run_type=run_type,
            dag_run=dag_run,
            task_states=task_states,
            snapshot=snapshot,
            error_summary=error_summary,
        )

        html_body = _build_html_body(
            status=status,
            pipeline_name=pipeline_name,
            run_type=run_type,
            dag_run=dag_run,
            task_states=task_states,
            snapshot=snapshot,
            error_summary=error_summary,
        )

        _send_email(
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )

        print(
            f"[Career Radar] {status} notification sent "
            f"for DAG {dag_id}, run {dag_run.run_id}."
        )

    except Exception as exc:
        # Notification failure must never change pipeline status.
        print(
            "[Career Radar] Notification failed: "
            f"{type(exc).__name__}: {exc}"
        )


def notify_dag_success(context):
    _notify(
        context=context,
        status="SUCCESS",
    )


def notify_dag_failure(context):
    _notify(
        context=context,
        status="FAILED",
    )
