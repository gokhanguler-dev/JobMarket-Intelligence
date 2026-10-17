import unittest

from ingestion.parsers.skill_extractor import (
    extract_skills
)


class TestSkillExtractor(unittest.TestCase):

    def test_multiple_skills(self):

        text = (
            "We are looking for a Data Engineer "
            "with Python, Apache Spark, "
            "Databricks and AWS experience."
        )

        result = extract_skills(text)

        self.assertIn("Python", result)
        self.assertIn("Spark", result)
        self.assertIn("Databricks", result)
        self.assertIn("AWS", result)

    def test_gcp_alias(self):

        text = (
            "Build scalable solutions on "
            "Google Cloud Platform using Terraform."
        )

        result = extract_skills(text)

        self.assertIn("GCP", result)
        self.assertIn("Terraform", result)

    def test_empty_text(self):

        result = extract_skills(None)

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()