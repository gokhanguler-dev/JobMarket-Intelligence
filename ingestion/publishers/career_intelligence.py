from collections import Counter
from datetime import timedelta
from functools import lru_cache

from ingestion.parsers.capability_extractor import extract_capabilities
from ingestion.parsers.job_text_parser import clean_html_text
from ingestion.parsers.skill_extractor import extract_skills, load_skill_taxonomy


PROFILE_ROLES = ("Data Engineer", "AI Engineer")
SIGNAL_GROUPS = ("technologies", "capabilities")

# A job can contribute its first observation and its latest observation in a
# week. The two are distinct when its description changes after discovery.
OBSERVATION_QUERY = """
WITH observed AS (
    SELECT f.JobPostingKey, f.CompanyKey, f.SourceSystem,
           ca.CareerAreaName, role.RoleName,
           o.JobObservationKey, o.RawJobPostingID, o.ObservedAt,
           CAST(o.ObservedAt AT TIME ZONE 'UTC' AT TIME ZONE 'Turkey Standard Time' AS date) AS LocalDay
    FROM dwh.FactJobObservation o
    JOIN dwh.FactJobPosting f ON f.JobPostingKey = o.JobPostingKey
    LEFT JOIN dwh.DimCareerArea ca ON ca.CareerAreaKey = f.CareerAreaKey
    LEFT JOIN dwh.DimRole role ON role.RoleKey = f.RoleKey
    WHERE f.IsTechRole = 'Tech'
),
weeks AS (
    SELECT *,
           CAST(DATEADD(day, -DATEDIFF(day, '19000101', LocalDay) % 7, LocalDay) AS date) AS WeekStart
    FROM observed
),
coverage AS (
    SELECT WeekStart, MIN(LocalDay) AS FirstDay, MAX(LocalDay) AS LastDay,
           COUNT(DISTINCT LocalDay) AS ObservedDays
    FROM weeks
    GROUP BY WeekStart
),
ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY JobPostingKey, WeekStart ORDER BY ObservedAt DESC, JobObservationKey DESC
           ) AS WeeklyRank,
           ROW_NUMBER() OVER (
               PARTITION BY JobPostingKey ORDER BY ObservedAt, JobObservationKey
           ) AS FirstRank,
           ROW_NUMBER() OVER (
               PARTITION BY JobPostingKey ORDER BY ObservedAt DESC, JobObservationKey DESC
           ) AS LatestRank
    FROM weeks
)
SELECT r.JobPostingKey, r.CompanyKey, r.SourceSystem, r.RoleName, r.CareerAreaName,
       r.LocalDay, r.WeekStart, w.FirstDay, w.LastDay, w.ObservedDays,
       r.WeeklyRank, r.FirstRank, r.LatestRank,
       raw.JobTitle, COALESCE(NULLIF(raw.Description, ''), raw.Snippet) AS Description
FROM ranked r
JOIN coverage w ON w.WeekStart = r.WeekStart
LEFT JOIN stg.JobPostingRaw raw ON raw.RawJobPostingID = r.RawJobPostingID
WHERE r.WeeklyRank = 1 OR r.FirstRank = 1
ORDER BY r.JobPostingKey, r.ObservedAt, r.JobObservationKey;
"""


class Demand:
    def __init__(self):
        self.jobs = 0
        self.companies = set()
        self.sources = set()
        self.signals = {group: Counter() for group in SIGNAL_GROUPS}

    def add(self, row, signals):
        self.jobs += 1
        if row["CompanyKey"] is not None:
            self.companies.add(row["CompanyKey"])
        self.sources.add(row["SourceSystem"])
        for group, names in zip(SIGNAL_GROUPS, signals):
            self.signals[group].update(names)

    def summarize(self):
        return {
            "jobs": self.jobs,
            "companies": len(self.companies),
            "sources": sorted(self.sources),
            **{
                group: [
                    {"name": name, "jobs": count}
                    for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
                ]
                for group, counter in self.signals.items()
            },
        }


def build_career_intelligence(rows, today):
    skill_taxonomy = load_skill_taxonomy()

    @lru_cache(maxsize=4096)
    def extract(title, description, area, role):
        text = clean_html_text(description) or ""
        technologies = frozenset(extract_skills(f"{title or ''} {text}", skill_taxonomy))
        capabilities = frozenset(
            match["capability"] for match in extract_capabilities(description, area, role)
        )
        return technologies, capabilities

    window_start = today - timedelta(days=29)
    profiles = {role: Demand() for role in PROFILE_ROLES}
    weeks = {}

    for row in rows:
        role = row["RoleName"]
        signals = extract(
            row["JobTitle"], row["Description"], row["CareerAreaName"], role
        )
        week_start = row["WeekStart"]
        if week_start not in weeks:
            weeks[week_start] = {
                "start": week_start,
                "first_day": row["FirstDay"],
                "last_day": row["LastDay"],
                "observed_days": row["ObservedDays"],
                "active": Demand(),
                "new": Demand(),
            }
        week = weeks[week_start]
        if row["WeeklyRank"] == 1:
            week["active"].add(row, signals)
        if row["FirstRank"] == 1:
            week["new"].add(row, signals)
        if row["LatestRank"] == 1 and role in profiles and window_start <= row["LocalDay"] <= today:
            profiles[role].add(row, signals)

    return {
        "profile_start": window_start,
        "profile_end": today,
        "roles": [
            {"role": role, **demand.summarize()} for role, demand in profiles.items()
        ],
        "weeks": [
            {**week, "active": week["active"].summarize(), "new": week["new"].summarize()}
            for _, week in sorted(weeks.items())
        ],
    }
