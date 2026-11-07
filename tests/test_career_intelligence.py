import unittest
from datetime import date

from ingestion.publishers.career_intelligence import build_career_intelligence


class TestCareerIntelligence(unittest.TestCase):
    def observation(self, *, week, day, first, latest, weekly, title, description):
        return {
            "JobPostingKey": 1,
            "RoleName": "AI Engineer",
            "CareerAreaName": "AI & Machine Learning",
            "CompanyKey": 4,
            "SourceSystem": "Workable",
            "JobTitle": title,
            "Description": description,
            "LocalDay": day,
            "WeekStart": week,
            "FirstDay": day,
            "LastDay": day,
            "ObservedDays": 1,
            "WeeklyRank": weekly,
            "FirstRank": first,
            "LatestRank": latest,
        }

    def test_first_seen_and_weekly_demand_use_their_own_snapshots(self):
        week = date(2026, 10, 19)
        rows = [
            self.observation(week=week, day=week, first=1, latest=3, weekly=2,
                             title="AI Engineer", description="Python."),
            self.observation(week=week, day=week, first=2, latest=2, weekly=1,
                             title="AI Engineer", description="SQL. Deploy ML models."),
            self.observation(week=date(2026, 10, 26), day=date(2026, 10, 26),
                             first=3, latest=1, weekly=1, title="AI Engineer",
                             description="Build RAG systems with Python."),
        ]
        result = build_career_intelligence(rows, date(2026, 11, 1))
        initial, following = result["weeks"]
        self.assertEqual(initial["new"]["jobs"], 1)
        self.assertEqual(initial["new"]["technologies"], [{"name": "Python", "jobs": 1}])
        self.assertEqual(initial["active"]["jobs"], 1)
        self.assertEqual(initial["active"]["technologies"], [{"name": "SQL", "jobs": 1}])
        self.assertIn({"name": "Model Deployment & Monitoring", "jobs": 1},
                      initial["active"]["capabilities"])
        self.assertEqual(following["new"]["jobs"], 0)
        self.assertEqual(following["active"]["jobs"], 1)
        role = next(profile for profile in result["roles"] if profile["role"] == "AI Engineer")
        self.assertEqual(role["jobs"], 1)
        self.assertIn({"name": "RAG & Retrieval Engineering", "jobs": 1}, role["capabilities"])

    def test_older_observations_stay_in_trends_and_leave_the_recent_profile(self):
        week = date(2026, 10, 19)
        row = self.observation(week=week, day=week, first=1, latest=1, weekly=1,
                               title="AI Engineer", description="Python.")
        result = build_career_intelligence([row], date(2026, 11, 19))
        self.assertEqual(result["weeks"][0]["active"]["jobs"], 1)
        self.assertEqual(sum(profile["jobs"] for profile in result["roles"]), 0)
