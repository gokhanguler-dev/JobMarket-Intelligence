import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from ingestion.collectors.workday_collector import fetch_all_job_summaries
from ingestion.publishers.role_opportunities import (
    BoardSnapshot,
    snapshot_for_board,
    summarize_opportunities,
)


NOW = datetime(2026, 11, 8, 8, tzinfo=timezone.utc)


class TestBoardSnapshots(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.raw = Path(directory.name)

    def write_lever(self, name, checked_at, jobs):
        path = self.raw / name
        path.write_text(json.dumps({
            "metadata": {
                "source_system": "Lever",
                "source_site": "demo",
                "result_count": len(jobs),
                "extracted_at": checked_at.isoformat(),
            },
            "response": {"jobs": jobs},
        }), encoding="utf-8")
        return path

    def test_successful_empty_snapshot_replaces_older_membership(self):
        self.write_lever("lever_demo_20261107_080000.json", NOW - timedelta(days=1), [{"id": "12345"}])
        empty = self.write_lever("lever_demo_20261108_080000.json", NOW, [])
        self.assertEqual(snapshot_for_board(self.raw, "Lever", {"site": "demo"}, NOW).filename, empty.name)

    def test_corrupt_latest_snapshot_does_not_fall_back(self):
        self.write_lever("lever_demo_20261107_080000.json", NOW - timedelta(days=1), [{"id": "12345"}])
        (self.raw / "lever_demo_20261108_080000.json").write_text("{", encoding="utf-8")
        self.assertIsNone(snapshot_for_board(self.raw, "Lever", {"site": "demo"}, NOW))

    def test_stale_snapshot_is_ineligible(self):
        self.write_lever("lever_demo_20261106_080000.json", NOW - timedelta(hours=48), [])
        self.assertIsNone(snapshot_for_board(self.raw, "Lever", {"site": "demo"}, NOW))

    def test_workday_requires_completed_list_and_details(self):
        path = self.raw / "workday_demo_20261108_080000.json"
        board = {"tenant": "demo", "site": "Careers", "host": "example.com", "location_facets": []}
        metadata = {
            **board,
            "source_system": "Workday",
            "extracted_at": NOW.isoformat(),
            "list_complete": True,
            "list_result_count": 1,
            "detail_result_count": 0,
            "failed_detail_count": 1,
        }
        path.write_text(json.dumps({"metadata": metadata, "jobs": []}), encoding="utf-8")
        self.assertIsNone(snapshot_for_board(self.raw, "Workday", board, NOW))
        metadata.update(detail_result_count=1, failed_detail_count=0)
        path.write_text(json.dumps({"metadata": metadata, "jobs": [{"summary": {"externalPath": "/job/one"}, "jobPostingInfo": {"title": "Engineer"}}]}), encoding="utf-8")
        self.assertEqual(snapshot_for_board(self.raw, "Workday", board, NOW).filename, path.name)


class TestOpportunitySelection(unittest.TestCase):
    def test_requires_current_snapshot_turkiye_and_a_posting_link(self):
        row = {
            "JobPostingKey": 7, "CompanyKey": 1, "SourceSystem": "Lever", "SourceJobID": "seven",
            "CompanyName": "Example", "RoleName": "AI Engineer", "CareerAreaName": "AI & Machine Learning",
            "JobTitle": "AI Engineer", "JobLocation": "Istanbul", "WorkModel": None,
            "JobLink": "https://jobs.lever.co/example/eb67ca23-46a1-44ae-ac15-7df84bd7dac0",
            "RawFileName": "latest.json", "Description": "Build RAG systems with Python.", "DaysSeen": 5,
        }
        boards = {"latest.json": BoardSnapshot("latest.json", "Lever", NOW, frozenset({"seven"}))}
        report = summarize_opportunities([
            row,
            {**row, "JobPostingKey": 8, "RawFileName": "older.json"},
            {**row, "JobPostingKey": 9, "JobLocation": "Berlin, Germany"},
            {**row, "JobPostingKey": 10, "JobLink": "javascript:alert(12345)"},
            {**row, "JobPostingKey": 11, "SourceSystem": "Jooble"},
            {**row, "JobPostingKey": 12, "SourceJobID": "removed-from-board"},
        ], boards, NOW)
        self.assertEqual([job["id"] for job in report["jobs"]], [7])
        self.assertEqual(report["jobs"][0]["days_seen"], 5)
        self.assertEqual(report["jobs"][0]["expires_at"], NOW + timedelta(hours=48))
        self.assertIn("RAG & Retrieval Engineering", report["jobs"][0]["capabilities"])
        self.assertIn("Python", report["jobs"][0]["technologies"])
        self.assertNotIn("description", report["jobs"][0])


class TestWorkdayPageCompleteness(unittest.TestCase):
    def test_rejects_a_truncated_workday_list(self):
        with patch("ingestion.collectors.workday_collector.fetch_job_page", return_value={
            "total": 2, "jobPostings": [{"externalPath": "/job/only-one"}],
        }):
            with self.assertRaisesRegex(ValueError, "Incomplete Workday"):
                fetch_all_job_summaries(None, {"company": "Example"})

    def test_accepts_a_complete_workday_list(self):
        jobs = [{"externalPath": "/job/one"}, {"externalPath": "/job/two"}]
        with patch("ingestion.collectors.workday_collector.fetch_job_page", return_value={
            "total": len(jobs), "jobPostings": jobs,
        }):
            self.assertEqual(fetch_all_job_summaries(None, {"company": "Example"}), jobs)
