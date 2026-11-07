"""Publish recently observed vacancies from verified employer-board snapshots."""

import json
import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

from ingestion.loaders.workday_raw_loader import get_source_job_id
from ingestion.parsers.capability_extractor import extract_capabilities
from ingestion.parsers.job_text_parser import clean_html_text
from ingestion.parsers.skill_extractor import extract_skills, load_skill_taxonomy
from ingestion.publishers.career_intelligence import PROFILE_ROLES
from ingestion.publishers.role_posting_audit import (
    ELIGIBLE_SCOPES,
    audit_role_postings,
    posting_url,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BOARD_SOURCES = {
    "Lever": ("site", "source_site"),
    "Greenhouse": ("board_token", "source_board"),
    "Workable": ("account", "source_account"),
    "Workday": ("tenant", "tenant"),
}
SNAPSHOT_TIMESTAMP = re.compile(r"\d{8}_\d{6}(?:_\d{6})?\.json")
WINDOW_DAYS = 10
MIN_DAYS_SEEN = 2
MAX_BOARD_AGE = timedelta(hours=48)
MAX_PER_ROLE = 8


OPPORTUNITY_QUERY = """
WITH current_postings AS (
    SELECT f.JobPostingKey, f.CompanyKey, f.SourceSystem, raw.SourceJobID,
           role.RoleName, ca.CareerAreaName,
           c.CompanyName, raw.JobTitle, raw.JobLocation, raw.WorkModel, raw.JobLink,
           raw.RawFileName, COALESCE(NULLIF(raw.Description, ''), raw.Snippet) AS Description
    FROM stg.JobPostingRaw raw
    JOIN dwh.FactJobPosting f ON f.SourceSystem = raw.SourceSystem
                             AND f.SourceJobID = raw.SourceJobID
    JOIN dwh.DimRole role ON role.RoleKey = f.RoleKey
    JOIN dwh.DimCareerArea ca ON ca.CareerAreaKey = f.CareerAreaKey
    LEFT JOIN dwh.DimCompany c ON c.CompanyKey = f.CompanyKey
    WHERE raw.RawFileName IN ({files})
      AND f.IsTechRole = 'Tech'
      AND role.RoleName IN ({roles})
),
history AS (
    SELECT o.JobPostingKey,
           COUNT(DISTINCT CAST(raw.ExtractedAt AT TIME ZONE 'Turkey Standard Time' AS date)) AS DaysSeen
    FROM (SELECT DISTINCT JobPostingKey FROM current_postings) p
    JOIN dwh.FactJobObservation o ON o.JobPostingKey = p.JobPostingKey
    JOIN stg.JobPostingRaw raw ON raw.RawJobPostingID = o.RawJobPostingID
    WHERE raw.ExtractedAt >= CONVERT(datetimeoffset, ?)
      AND raw.ExtractedAt <= CONVERT(datetimeoffset, ?)
    GROUP BY o.JobPostingKey
)
SELECT p.*, h.DaysSeen
FROM current_postings p
JOIN history h ON h.JobPostingKey = p.JobPostingKey
WHERE h.DaysSeen >= ?;
"""


@dataclass(frozen=True)
class BoardSnapshot:
    filename: str
    source: str
    checked_at: datetime
    job_ids: frozenset


def snapshot_for_board(raw_dir, source, board, now):
    config_key, metadata_key = BOARD_SOURCES[source]
    identity = board[config_key]
    file_identity = identity.lower().replace(" ", "_") if source == "Workday" else identity
    prefix = f"{source.lower()}_{file_identity}_"
    paths = sorted(raw_dir.glob(f"{prefix}*.json"), reverse=True)

    for path in paths:
        if not SNAPSHOT_TIMESTAMP.fullmatch(path.name[len(prefix):]):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            metadata = payload["metadata"]
            if metadata["source_system"] != source or metadata[metadata_key] != identity:
                return None
            if source == "Workday":
                if any(metadata.get(key) != board.get(key) for key in ("site", "host", "location_facets")):
                    continue
                jobs = payload["jobs"]
                complete = (
                    metadata.get("list_complete") is True
                    and metadata["list_result_count"] == metadata["detail_result_count"] == len(jobs)
                    and metadata["failed_detail_count"] == 0
                )
            else:
                jobs = payload["response"]["jobs"]
                complete = metadata["result_count"] == len(jobs)

            if not isinstance(jobs, list) or not all(isinstance(job, dict) for job in jobs):
                return None
            if source == "Workday":
                identifiers = [
                    get_source_job_id(job["summary"], job["jobPostingInfo"])
                    if job["summary"].get("externalPath")
                    and isinstance(job["jobPostingInfo"], dict) and job["jobPostingInfo"]
                    else None
                    for job in jobs
                ]
            else:
                id_key = "shortcode" if source == "Workable" else "id"
                identifiers = [job.get(id_key) for job in jobs]
                if source == "Workable":
                    identifiers = [f"{identity}:{job_id}" if job_id else None for job_id in identifiers]

            checked_at = datetime.fromisoformat(metadata["extracted_at"].replace("Z", "+00:00"))
            if (
                complete and all(identifiers) and len(set(identifiers)) == len(jobs)
                and checked_at.tzinfo is not None and now - MAX_BOARD_AGE < checked_at <= now
            ):
                return BoardSnapshot(path.name, source, checked_at, frozenset(map(str, identifiers)))
        except (OSError, ValueError, TypeError, AttributeError, KeyError):
            return None

        # A newer invalid or incomplete check must never revive an older listing.
        return None

    return None


def load_latest_boards(now, project_root=PROJECT_ROOT):
    snapshots = {}
    for source in BOARD_SOURCES:
        config_path = project_root / "config" / f"{source.lower()}_sources.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        for board in config["sources"]:
            if board.get("enabled", True):
                snapshot = snapshot_for_board(project_root / "data" / "raw", source, board, now)
                if snapshot is not None:
                    snapshots[snapshot.filename] = snapshot
    return snapshots


def load_opportunity_rows(cursor, snapshots, now):
    if not snapshots:
        return []

    start = datetime.combine(now.date() - timedelta(days=WINDOW_DAYS - 1), time.min, now.tzinfo)
    query = OPPORTUNITY_QUERY.format(
        files=", ".join("?" for _ in snapshots),
        roles=", ".join("?" for _ in PROFILE_ROLES),
    )
    cursor.execute(
        query,
        *snapshots,
        *PROFILE_ROLES,
        start.astimezone(timezone.utc).isoformat(),
        now.astimezone(timezone.utc).isoformat(),
        MIN_DAYS_SEEN,
    )
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def summarize_opportunities(rows, snapshots, now):
    latest = {}
    for row in rows:
        snapshot = snapshots.get(row["RawFileName"])
        if (
            snapshot is None or snapshot.source != row["SourceSystem"]
            or str(row["SourceJobID"]) not in snapshot.job_ids
            or not row["CompanyName"] or not row["JobTitle"] or not posting_url(row["JobLink"])
        ):
            continue
        key = row["JobPostingKey"]
        if key not in latest or snapshot.checked_at > latest[key][1].checked_at:
            latest[key] = ({**row, "LocalDay": snapshot.checked_at.astimezone(now.tzinfo).date()}, snapshot)

    taxonomy = load_skill_taxonomy()
    jobs = []
    for role in PROFILE_ROLES:
        retained, _ = audit_role_postings(
            [row for row, _ in latest.values() if row["RoleName"] == role]
        )
        ranked = sorted(
            (posting for posting in retained if posting.scope in ELIGIBLE_SCOPES),
            key=lambda posting: (
                -posting.row["DaysSeen"],
                -latest[posting.row["JobPostingKey"]][1].checked_at.timestamp(),
                posting.row["JobPostingKey"],
            ),
        )
        for posting in ranked[:MAX_PER_ROLE]:
            row = posting.row
            snapshot = latest[row["JobPostingKey"]][1]
            checked_at = snapshot.checked_at.astimezone(now.tzinfo)
            description = clean_html_text(row["Description"]) or ""
            jobs.append({
                "id": row["JobPostingKey"],
                "role": role,
                "title": row["JobTitle"],
                "company": row["CompanyName"],
                "location": row["JobLocation"],
                "scope": posting.scope,
                "source": snapshot.source,
                "url": row["JobLink"].strip(),
                "checked_at": checked_at,
                "expires_at": checked_at + MAX_BOARD_AGE,
                "days_seen": row["DaysSeen"],
                "technologies": sorted(extract_skills(f"{row['JobTitle']} {description}", taxonomy)),
                "capabilities": sorted(match["capability"] for match in extract_capabilities(
                    row["Description"], row["CareerAreaName"], role
                )),
            })
    return {
        "window_days": WINDOW_DAYS,
        "window_end": now.date(),
        "minimum_days": MIN_DAYS_SEEN,
        "jobs": jobs,
    }
