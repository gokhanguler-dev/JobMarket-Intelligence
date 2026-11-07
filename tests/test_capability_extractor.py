import unittest

from ingestion.parsers.capability_extractor import extract_capabilities


RAG = "RAG & Retrieval Engineering"
MODEL_OPS = "Model Deployment & Monitoring"
DATA_QUALITY = "Data Quality & Validation"


class TestExplicitCapabilityEvidence(unittest.TestCase):
    def capabilities(self, text, role="AI Engineer", area="AI & Machine Learning"):
        return {match["capability"] for match in extract_capabilities(text, area, role)}

    def test_rag_implementation_and_hands_on_experience(self):
        for description in (
            "Architect and construct RAG document ingestion pipelines.",
            "Practical experience designing and implementing RAG systems.",
            "You will build retrieval-augmented generation systems.",
        ):
            with self.subTest(description=description):
                self.assertIn(RAG, self.capabilities(description))

    def test_rag_mentions_do_not_count_as_implementation(self):
        for description in (
            "Familiarity with RAG, function calling, and vector databases.",
            "Agentic patterns include RAG and MCP.",
            "No need to build RAG pipelines in this role.",
            "The ability to implement RAG systems is a plus.",
        ):
            with self.subTest(description=description):
                self.assertNotIn(RAG, self.capabilities(description))

    def test_preferred_section_stops_at_responsibilities(self):
        text = """
        <h3>Preferred Qualifications</h3>
        <ul><li>Ability to implement RAG systems.</li></ul>
        <h3>Responsibilities</h3>
        <ul><li>Deploy machine learning models.</li></ul>
        """
        capabilities = self.capabilities(text)
        self.assertNotIn(RAG, capabilities)
        self.assertIn(MODEL_OPS, capabilities)

    def test_model_monitoring_is_distinct_from_mlops_familiarity(self):
        self.assertIn(
            MODEL_OPS,
            self.capabilities("Write robust code to support model monitoring."),
        )
        self.assertNotIn(
            MODEL_OPS,
            self.capabilities("Familiarity with MLflow and MLOps practices."),
        )

    def test_data_quality_responsibility_uses_role_context(self):
        description = "Own data quality, governance, and observability."
        self.assertIn(
            DATA_QUALITY,
            self.capabilities(description, "Data Engineer", "Data & Analytics"),
        )
        self.assertNotIn(
            DATA_QUALITY,
            self.capabilities(description, "Recruiter", "Out of Scope"),
        )

    def test_turkish_responsibility_matches(self):
        self.assertIn(
            DATA_QUALITY,
            self.capabilities(
                "Veri kalitesi kontrolleri geliştirmek.",
                "Data Engineer",
                "Data & Analytics",
            ),
        )
