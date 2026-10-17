import unittest

from ingestion.parsers.job_classifier import (
    classify_role,
    classify_seniority,
    classify_job
)


class TestJobClassifier(unittest.TestCase):

    def test_data_engineer_role(self):
        title = "Senior Data Software Engineer"

        self.assertEqual(
            classify_role(title),
            "Data Engineer"
        )

    def test_data_integration_engineer(self):
        title = "Senior Data Integration Engineer"

        self.assertEqual(
            classify_role(title),
            "Data Engineer"
        )

    def test_software_engineer_role(self):
        title = "Lead Full-Stack Engineer (Python Data)"

        self.assertEqual(
            classify_role(title),
            "Software Engineer"
        )

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

    def test_empty_title(self):
        result = classify_job(None)

        self.assertEqual(
            result["normalized_role"],
            "Unknown"
        )

        self.assertEqual(
            result["seniority"],
            "Unknown"
        )

    def test_data_architect(self):
        self.assertEqual(
            classify_role("Data Solution Architect"),
            "Data Architect"
        )

    def test_data_devops_engineer(self):
        self.assertEqual(
            classify_role("Senior Data DevOps Engineer with Azure"),
            "Data DevOps Engineer"
        )

    def test_bi_analyst(self):
        self.assertEqual(
            classify_role("Senior BI Analyst"),
            "BI Analyst"
        )

    def test_ai_engineer(self):
        self.assertEqual(
            classify_role("Senior AI Engineer with Databricks"),
            "AI Engineer"
        )

    def test_business_analyst(self):
        self.assertEqual(
            classify_role("Lead Business Analyst (ServiceNow)"),
            "Business Analyst"
        )

    def test_financial_analyst(self):
        self.assertEqual(
            classify_role("Junior Financial Analyst (Hybrid)"),
            "Financial Analyst"
        )

    def test_unrelated_developer_remains_other(self):
        self.assertEqual(
            classify_role("Senior ABAP Developer"),
            "Other"
        )


if __name__ == "__main__":
    unittest.main()