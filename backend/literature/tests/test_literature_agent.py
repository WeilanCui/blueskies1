"""Tests for literature LLM enrichment (stub + mocked OpenAI)."""

from unittest import mock

from django.test import SimpleTestCase, TestCase

from literature.enrichment.extractors import (
    ExtractionContext,
    OpenAIExtractor,
    StubExtractor,
    _validate_extraction,
)
from literature.enrichment.literature_agent import enrich_literature_link
from core.models import (
    Compound,
    PropertyAssertion,
    SourceType,
)
from literature.models import (
    CompoundLiterature,
    LiteratureEnrichmentStatus,
    LiteratureReference,
    RelevanceCategory,
    RoleInPaper,
)
from literature.seeds.loader import upsert_property_definitions

XML_PRESERVATIVE_SURVEY = """<?xml version="1.0"?>
<PubmedArticleSet>
 <PubmedArticle>
  <MedlineCitation>
   <PMID>39153997</PMID>
   <Article>
    <Journal><Title>Cosmetics</Title>
     <JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue>
    </Journal>
    <ArticleTitle>Deciphering trends in replacing preservatives in cosmetics intended for infants and sensitive population.</ArticleTitle>
    <Abstract>
     <AbstractText>Eleven alternative ingredients with antimicrobial activities, including 1,2-hexanediol, are discussed as multifunctional preservatives replacing conventional preservatives in cosmetic products.</AbstractText>
    </Abstract>
    <ELocationID EIdType="doi">10.3390/cosmetics11080245</ELocationID>
   </Article>
   <MeshHeadingList>
    <MeshHeading><DescriptorName>Cosmetics</DescriptorName></MeshHeading>
    <MeshHeading><DescriptorName>Preservatives, Pharmaceutical</DescriptorName></MeshHeading>
   </MeshHeadingList>
  </MedlineCitation>
  <PubmedData>
   <ArticleIdList>
    <ArticleId IdType="pubmed">39153997</ArticleId>
    <ArticleId IdType="pmc">PMC11345678</ArticleId>
    <ArticleId IdType="doi">10.3390/cosmetics11080245</ArticleId>
   </ArticleIdList>
  </PubmedData>
 </PubmedArticle>
</PubmedArticleSet>"""


class ExtractorValidationTests(SimpleTestCase):
    def test_drops_out_of_vocab_and_clamps_confidence(self):
        extraction = _validate_extraction(
            {
                "relevance_category": "not_a_real_category",
                "role_in_paper": "wizard",
                "functional_classes": ["preservative", "wizard_class"],
                "evidence_summary": "test",
                "confidence": 9.5,
            }
        )
        self.assertEqual(extraction.relevance_category, RelevanceCategory.GENERAL)
        self.assertEqual(extraction.role_in_paper, RoleInPaper.UNKNOWN)
        self.assertEqual(extraction.functional_classes, ["preservative"])
        self.assertEqual(extraction.confidence, 1.0)


class OpenAIExtractorTests(SimpleTestCase):
    def test_parses_mocked_openai_response(self):
        payload = (
            '{"relevance_category":"preservation_performance",'
            '"role_in_paper":"co_ingredient",'
            '"functional_classes":["preservative"],'
            '"evidence_summary":"Listed as antimicrobial alternative.",'
            '"confidence":0.82}'
        )
        mock_response = mock.Mock()
        mock_response.choices = [mock.Mock(message=mock.Mock(content=payload))]
        mock_client = mock.Mock()
        mock_client.chat.completions.create.return_value = mock_response

        with mock.patch("openai.OpenAI", return_value=mock_client):
            extractor = OpenAIExtractor(api_key="test-key", model="gpt-4o-mini")
            result = extractor.extract(
                ExtractionContext(
                    inci_name="1,2-HEXANEDIOL",
                    title="Preservative survey",
                    abstract="1,2-hexanediol as antimicrobial preservative.",
                    mesh_terms=["Preservatives, Pharmaceutical"],
                )
            )

        self.assertEqual(
            result.relevance_category, RelevanceCategory.PRESERVATION_PERFORMANCE
        )
        self.assertEqual(result.functional_classes, ["preservative"])
        self.assertEqual(result.confidence, 0.82)


class LiteratureAgentTests(TestCase):
    def setUp(self):
        upsert_property_definitions()
        self.compound = Compound.objects.create(canonical_inci="1,2-HEXANEDIOL")
        self.reference = LiteratureReference.objects.create(
            pmid="39153997",
            title="Deciphering trends in replacing preservatives in cosmetics intended for infants and sensitive population.",
            abstract=(
                "Eleven alternative ingredients with antimicrobial activities, "
                "including 1,2-hexanediol, are discussed as multifunctional preservatives."
            ),
            mesh_terms=["Cosmetics", "Preservatives, Pharmaceutical"],
            url="https://pubmed.ncbi.nlm.nih.gov/39153997/",
        )
        self.link = CompoundLiterature.objects.create(
            compound=self.compound,
            literature=self.reference,
            relevance_category=RelevanceCategory.SIDE_EFFECT,
            role_in_paper=RoleInPaper.UNKNOWN,
            confidence=0.5,
            evidence_summary="Rule pass",
            source_type=SourceType.LITERATURE,
            source_ref="pubmed:39153997",
        )

    def test_stub_enriches_preservative_fixture(self):
        extraction = enrich_literature_link(self.link, extractor=StubExtractor())
        self.assertIsNotNone(extraction)
        assert extraction is not None
        self.link.refresh_from_db()
        self.assertEqual(self.link.enrichment_status, LiteratureEnrichmentStatus.ENRICHED)
        self.assertEqual(self.link.enriched_by, "stub")
        self.assertIn("preservative", extraction.functional_classes)

        assertion = PropertyAssertion.objects.get(
            compound=self.compound,
            property_def__key="functional_class",
            source_ref="pubmed:39153997",
        )
        self.assertEqual(assertion.source_type, SourceType.LITERATURE)
        self.assertIn("preservative", assertion.value_json)
        self.assertTrue(assertion.is_active)

    def test_extractor_failure_leaves_rule_values(self):
        class BoomExtractor(StubExtractor):
            name = "boom"

            def extract(self, context):
                raise RuntimeError("extractor down")

        enrich_literature_link(self.link, extractor=BoomExtractor())
        self.link.refresh_from_db()
        self.assertEqual(self.link.enrichment_status, LiteratureEnrichmentStatus.FAILED)
        self.assertEqual(self.link.relevance_category, RelevanceCategory.SIDE_EFFECT)
        self.assertEqual(self.link.role_in_paper, RoleInPaper.UNKNOWN)

    def test_does_not_downgrade_human_functional_class(self):
        from core.models import PropertyDefinition

        prop = PropertyDefinition.objects.get(key="functional_class")
        human = PropertyAssertion.objects.create(
            compound=self.compound,
            property_def=prop,
            value_json=["humectant"],
            source_type=SourceType.HUMAN,
            source_ref="human:reviewer",
            confidence=0.95,
            is_active=True,
        )
        enrich_literature_link(self.link, extractor=StubExtractor())
        human.refresh_from_db()
        self.assertTrue(human.is_active)

        lit = PropertyAssertion.objects.get(
            compound=self.compound,
            source_ref="pubmed:39153997",
        )
        self.assertFalse(lit.is_active)
        self.assertEqual(lit.superseded_by_id, human.pk)
