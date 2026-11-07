import unittest

from ingestion.loaders.workable_raw_loader import clean_html_text, turkey_location


class TestWorkableRawLoader(unittest.TestCase):
    def test_turkish_secondary_location(self):
        job = {
            "country": "Germany",
            "locations": [
                {"countryCode": "DE", "city": "Berlin"},
                {"countryCode": "TR", "city": "Istanbul"},
            ],
        }
        self.assertEqual(turkey_location(job), "Istanbul, Turkey")

    def test_remote_job_outside_turkey(self):
        job = {"country": "Germany", "telecommuting": True}
        self.assertIsNone(turkey_location(job))

    def test_turkish_primary_country(self):
        job = {"country": "TÜRKİYE", "city": "Ankara"}
        self.assertEqual(turkey_location(job), "Ankara, Turkey")

    def test_html_description_keeps_skill_boundaries(self):
        description = "<ul><li>Python</li><li>SQL</li><li>C#</li></ul>"
        self.assertEqual(clean_html_text(description), "Python\nSQL\nC#")
