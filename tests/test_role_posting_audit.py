import unittest
from datetime import date

from ingestion.publishers.role_posting_audit import audit_role_postings, market_scope, posting_url


EXCERPT_A = "Build scalable ingestion pipelines that support reliable reporting across several business teams"
EXCERPT_B = "Maintain observability and monitoring so downstream data products can meet service expectations"
DIRECT_DESCRIPTION = f"{EXCERPT_A}. Own the operational handover. {EXCERPT_B}."
AGGREGATOR_DESCRIPTION = f"...{EXCERPT_A}... ...{EXCERPT_B}..."


def posting(key, source, *, url=None, company=1, location="Istanbul", description=DIRECT_DESCRIPTION):
    return {
        "JobPostingKey": key,
        "SourceSystem": source,
        "JobTitle": "Senior Cloud Data Engineer",
        "CompanyKey": company,
        "JobLocation": location,
        "WorkModel": None,
        "JobLink": url,
        "Description": description,
        "LocalDay": date(2026, 11, 7),
    }


class TestMarketScope(unittest.TestCase):
    def test_turkish_city_and_hybrid_are_local(self):
        self.assertEqual(market_scope("İstanbul / Maslak", "Hybrid", "", "", "Lever"), "turkiye")
        self.assertEqual(market_scope("Türkiye", None, "", "", "Workable"), "turkiye")

    def test_remote_requires_eligibility_evidence(self):
        self.assertEqual(
            market_scope("Evden çalışmak", None, "Engineer", "We are hiring an engineer based in Turkey.", "Jooble"),
            "remote_from_turkiye",
        )
        self.assertEqual(market_scope("Remote EMEA", None, "", "", "Lever"), "unknown")
        self.assertEqual(market_scope("Remote, Germany", None, "", "", "Lever"), "outside_turkiye")
        self.assertEqual(
            market_scope("Remote EMEA", None, "", "Our company is based in Turkey.", "Jooble"),
            "unknown",
        )

    def test_country_label_alone_and_foreign_relocation(self):
        self.assertEqual(market_scope("Türkiye", None, "", "", "Jooble"), "aggregator_location_only")
        self.assertEqual(
            market_scope("Türkiye", None, "Engineer (Relocation to Qatar)", "", "Jooble"),
            "outside_turkiye",
        )

    def test_explicit_on_site_model_overrides_remote_benefits(self):
        self.assertEqual(
            market_scope("Istanbul", "On-site", "Engineer",
                         "Employees can work remotely from Turkey during holidays.", "Lever"),
            "turkiye",
        )
        self.assertEqual(market_scope("Worldwide", "Remote", "", "", "Lever"), "remote_from_turkiye")

    def test_hybrid_perk_does_not_make_a_city_based_posting_remote(self):
        self.assertEqual(
            market_scope("İstanbul", None, "", "One week each month is fully remote.", "Workday"),
            "turkiye",
        )


class TestRoleDuplicateAudit(unittest.TestCase):
    def test_url_removes_tracking_and_keeps_requisition_identity(self):
        self.assertEqual(
            posting_url("https://example.com/job/12345/?utm_source=email&jobId=900"),
            posting_url("https://www.example.com/job/12345?jobId=900"),
        )
        self.assertNotEqual(
            posting_url("https://example.com/job/12345?jobId=900"),
            posting_url("https://example.com/job/12345?jobId=901"),
        )
        self.assertIsNone(posting_url("https://example.com/careers?utm_source=email"))
        self.assertIsNone(posting_url("javascript:alert(12345)"))

    def test_exact_url_prefers_direct_record(self):
        records = [
            posting(1, "Jooble", url="https://example.com/jobs/12345?utm_source=jooble"),
            posting(2, "Lever", url="https://example.com/jobs/12345"),
        ]
        retained, audit = audit_role_postings(records)
        self.assertEqual([item.row["JobPostingKey"] for item in retained], [2])
        self.assertEqual(audit["url_duplicates"], 1)
        self.assertEqual(audit["excerpt_duplicates"], 0)

    def test_two_excerpts_match_one_direct_record_even_if_aggregator_omits_employer(self):
        records = [
            posting(1, "Jooble", company=None, description=AGGREGATOR_DESCRIPTION),
            posting(2, "Workday"),
        ]
        retained, audit = audit_role_postings(records)
        self.assertEqual([item.row["JobPostingKey"] for item in retained], [2])
        self.assertEqual(audit["excerpt_duplicates"], 1)

    def test_generic_title_without_employer_is_review_only(self):
        records = [
            posting(1, "Jooble", company=None, description=AGGREGATOR_DESCRIPTION),
            posting(2, "Workday"),
        ]
        for record in records:
            record["JobTitle"] = "Data Engineer"
        retained, audit = audit_role_postings(records)
        self.assertEqual(len(retained), 2)
        self.assertEqual(audit["excerpt_duplicates"], 0)
        self.assertEqual(audit["possible_duplicate_records"], 2)

    def test_shared_url_with_different_titles_is_not_merged(self):
        records = [
            posting(1, "Lever", url="https://example.com/jobs/12345"),
            posting(2, "Jooble", url="https://example.com/jobs/12345"),
        ]
        records[1]["JobTitle"] = "Analytics Data Engineer"
        retained, audit = audit_role_postings(records)
        self.assertEqual(len(retained), 2)
        self.assertEqual(audit["url_duplicates"], 0)

    def test_ambiguous_matches_stay_in_the_sample(self):
        records = [
            posting(1, "Jooble", company=None, description=AGGREGATOR_DESCRIPTION),
            posting(2, "Workday", url="https://example.com/jobs/12345"),
            posting(3, "Lever", url="https://example.com/jobs/12346"),
        ]
        retained, audit = audit_role_postings(records)
        self.assertEqual(len(retained), 3)
        self.assertEqual(audit["excerpt_duplicates"], 0)
        self.assertEqual(audit["possible_duplicate_records"], 3)

    def test_same_title_with_distinct_employers_or_cities_does_not_merge(self):
        records = [
            posting(1, "Jooble", description=AGGREGATOR_DESCRIPTION),
            posting(2, "Workday", company=2),
            posting(3, "Lever", location="Ankara"),
        ]
        retained, audit = audit_role_postings(records)
        self.assertEqual(len(retained), 3)
        self.assertEqual(audit["possible_duplicate_records"], 0)

    def test_same_source_title_variants_require_review(self):
        records = [
            posting(1, "Jooble", url="https://tr.jooble.org/jdp/12345"),
            posting(2, "Jooble", url="https://tr.jooble.org/jdp/12346"),
        ]
        retained, audit = audit_role_postings(records)
        self.assertEqual(len(retained), 2)
        self.assertEqual(audit["possible_duplicate_records"], 2)
        self.assertEqual(sum(audit["locations"].values()), audit["distinct_postings"])
