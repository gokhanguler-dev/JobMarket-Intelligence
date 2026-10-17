import unittest

from ingestion.parsers.job_text_parser import clean_html_text


class TestJobTextParser(unittest.TestCase):

    def test_html_cleaning(self):

        raw_text = (
            "&nbsp;We're looking for a Senior "
            "<b>Data Engineer</b> with "
            "Apache Spark.&nbsp;"
        )

        expected = (
            "We're looking for a Senior "
            "Data Engineer with Apache Spark."
        )

        result = clean_html_text(raw_text)

        self.assertEqual(result, expected)

    def test_none(self):

        self.assertIsNone(
            clean_html_text(None)
        )

    def test_empty_string(self):

        self.assertIsNone(
            clean_html_text("")
        )


if __name__ == "__main__":
    unittest.main()