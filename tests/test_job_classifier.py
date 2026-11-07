import unittest

from ingestion.parsers.job_classifier import classify_job, classify_seniority


class TestJobClassifier(unittest.TestCase):
    def test_senior_seniority(self):
        title = "Senior Data Engineer, AI"

        self.assertEqual(
            classify_seniority(title),
            "Senior"
        )

    def test_lead_seniority(self):
        title = "Lead Data Engineer with Terraform"

        self.assertEqual(
            classify_seniority(title),
            "Lead"
        )

    def test_unspecified_seniority(self):
        title = "Data Engineer"

        self.assertEqual(
            classify_seniority(title),
            "Unspecified"
        )

    def test_complete_classification(self):
        title = (
            "Senior Data Engineer/ "
            "Databricks, PySpark, Python"
        )

        result = classify_job(title)

        self.assertEqual(
            result["normalized_role"],
            "Data Engineer"
        )

        self.assertEqual(
            result["seniority"],
            "Senior"
        )


if __name__ == "__main__":
    unittest.main()