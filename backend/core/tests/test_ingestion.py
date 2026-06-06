"""Mocked-HTTP tests for the PubChem + PubMed ingestion pipeline."""

from unittest import mock

from django.test import SimpleTestCase, TestCase

from core.ingestion import ingest_compound, pubchem_client, pubmed_client
from core.ingestion.pubchem_client import PubChemRecord
from core.ingestion.relevance import (
    build_ux_query,
    classify_relevance,
    infer_role_in_paper,
)
from core.models import (
    Compound,
    CompoundLiterature,
    CompoundRelationship,
    CompoundStructure,
    LiteratureReference,
    PropertyAssertion,
    RelevanceCategory,
    RoleInPaper,
)
from core.seeds.loader import upsert_property_definitions

# --- Fixtures ---------------------------------------------------------------

# PMID 39805611: 1,2-Hexanediol as the safety/irritation subject (synthetic fixture).
XML_HEXANEDIOL = """<?xml version="1.0"?>
<PubmedArticleSet>
 <PubmedArticle>
  <MedlineCitation>
   <PMID>39805611</PMID>
   <Article>
    <Journal><Title>Contact Dermatitis</Title>
     <JournalIssue><PubDate><Year>2025</Year></PubDate></JournalIssue>
    </Journal>
    <ArticleTitle>Skin irritation and sensitization potential of 1,2-Hexanediol</ArticleTitle>
    <Abstract>
     <AbstractText>1,2-Hexanediol is a common cosmetic humectant and solvent.</AbstractText>
     <AbstractText Label="RESULTS">Patch testing showed low allergic contact dermatitis risk.</AbstractText>
    </Abstract>
    <ELocationID EIdType="doi">10.1111/cod.99999</ELocationID>
   </Article>
   <MeshHeadingList>
    <MeshHeading><DescriptorName>Dermatitis, Allergic Contact</DescriptorName></MeshHeading>
    <MeshHeading><DescriptorName>Irritants</DescriptorName></MeshHeading>
   </MeshHeadingList>
   <ChemicalList>
    <Chemical><NameOfSubstance>Irritants</NameOfSubstance></Chemical>
   </ChemicalList>
  </MedlineCitation>
 </PubmedArticle>
</PubmedArticleSet>"""

# PMID 39203006: real metadata; 1,2-hexanediol is only the solvent for a plant extract.
XML_SUGARCANE = """<?xml version="1.0"?>
<PubmedArticleSet>
 <PubmedArticle>
  <MedlineCitation>
   <PMID>39203006</PMID>
   <Article>
    <Journal><Title>Molecules</Title>
     <JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue>
    </Journal>
    <ArticleTitle>New Natural and Sustainable Cosmetic Preservative Based on Sugarcane Straw Extract</ArticleTitle>
    <Abstract>
     <AbstractText>The 1,2-hexanediol was the solvent that allowed us to achieve the ingredient (20% dry extract dispersed in 25% 1,2-hexanediol in water) with the best antimicrobial performance.</AbstractText>
    </Abstract>
    <ELocationID EIdType="doi">10.3390/molecules29163928</ELocationID>
   </Article>
   <MeshHeadingList>
    <MeshHeading><DescriptorName>Anti-Infective Agents</DescriptorName></MeshHeading>
    <MeshHeading><DescriptorName>Antioxidants</DescriptorName></MeshHeading>
    <MeshHeading><DescriptorName>Cosmetics</DescriptorName></MeshHeading>
    <MeshHeading><DescriptorName>Microbial Sensitivity Tests</DescriptorName></MeshHeading>
    <MeshHeading><DescriptorName>Plant Extracts</DescriptorName></MeshHeading>
    <MeshHeading><DescriptorName>Preservatives, Pharmaceutical</DescriptorName></MeshHeading>
   </MeshHeadingList>
   <ChemicalList>
    <Chemical><NameOfSubstance>Cosmetics</NameOfSubstance></Chemical>
    <Chemical><NameOfSubstance>Plant Extracts</NameOfSubstance></Chemical>
    <Chemical><NameOfSubstance>Preservatives, Pharmaceutical</NameOfSubstance></Chemical>
    <Chemical><NameOfSubstance>Anti-Infective Agents</NameOfSubstance></Chemical>
    <Chemical><NameOfSubstance>Antioxidants</NameOfSubstance></Chemical>
   </ChemicalList>
  </MedlineCitation>
 </PubmedArticle>
</PubmedArticleSet>"""


# --- Pure / no-DB tests -----------------------------------------------------


class PubChemParsingTests(SimpleTestCase):
    def test_parse_properties_maps_descriptors(self):
        record = pubchem_client.parse_properties(
            {
                "CID": 8104,
                "MolecularFormula": "C6H14O2",
                "MolecularWeight": "118.17",
                "IsomericSMILES": "CCCCC(O)CO",
                "InChIKey": "FHKSXSQHXQEMOK-UHFFFAOYSA-N",
                "XLogP": 0.8,
                "TPSA": 40.5,
                "HBondDonorCount": 2,
                "HBondAcceptorCount": 2,
            }
        )
        self.assertEqual(record.cid, 8104)
        self.assertEqual(record.molecular_weight, 118.17)
        self.assertEqual(record.best_smiles, "CCCCC(O)CO")
        self.assertEqual(record.xlogp, 0.8)
        self.assertEqual(record.hbd, 2)

    def test_extract_cas(self):
        syns = ["1,2-Hexanediol", "6920-22-5", "Hexane-1,2-diol", "6920-22-5"]
        self.assertEqual(pubchem_client.extract_cas(syns), ["6920-22-5"])


class PubMedParsingTests(SimpleTestCase):
    def test_parse_hexanediol_fixture(self):
        [article] = pubmed_client.parse_efetch_xml(XML_HEXANEDIOL)
        self.assertEqual(article.pmid, "39805611")
        self.assertIn("1,2-Hexanediol", article.title)
        self.assertEqual(article.year, 2025)
        self.assertEqual(article.doi, "10.1111/cod.99999")
        self.assertIn("Irritants", article.mesh_terms)

    def test_parse_sugarcane_fixture(self):
        [article] = pubmed_client.parse_efetch_xml(XML_SUGARCANE)
        self.assertEqual(article.pmid, "39203006")
        self.assertEqual(article.journal, "Molecules")
        self.assertIn("Plant Extracts", article.substances)
        self.assertIn("Preservatives, Pharmaceutical", article.mesh_terms)


class RelevanceTests(SimpleTestCase):
    def test_query_includes_cosmetics_and_preservative_clauses(self):
        query = build_ux_query("1,2-Hexanediol")
        self.assertIn('"1,2-Hexanediol"[All Fields]', query)
        self.assertIn("cosmetics[mesh]", query)
        self.assertIn('"Preservatives, Pharmaceutical"[mesh]', query)

    def test_hexanediol_classified_as_side_effect_family(self):
        [article] = pubmed_client.parse_efetch_xml(XML_HEXANEDIOL)
        category = classify_relevance(
            article.mesh_terms, article.title, article.abstract
        )
        self.assertIn(
            category,
            {
                RelevanceCategory.SENSITIZATION,
                RelevanceCategory.IRRITATION,
                RelevanceCategory.SIDE_EFFECT,
                RelevanceCategory.SAFETY_PROFILE,
            },
        )

    def test_sugarcane_classified_as_preservation(self):
        [article] = pubmed_client.parse_efetch_xml(XML_SUGARCANE)
        category = classify_relevance(
            article.mesh_terms, article.title, article.abstract
        )
        self.assertEqual(category, RelevanceCategory.PRESERVATION_PERFORMANCE)

    def test_role_subject_vs_solvent(self):
        [hex_article] = pubmed_client.parse_efetch_xml(XML_HEXANEDIOL)
        self.assertEqual(
            infer_role_in_paper(
                "1,2-Hexanediol", hex_article.title, hex_article.abstract
            ),
            RoleInPaper.SUBJECT,
        )
        [cane_article] = pubmed_client.parse_efetch_xml(XML_SUGARCANE)
        self.assertEqual(
            infer_role_in_paper(
                "1,2-Hexanediol", cane_article.title, cane_article.abstract
            ),
            RoleInPaper.SOLVENT,
        )


# --- DB orchestration tests -------------------------------------------------


class IngestOrchestratorTests(TestCase):
    def setUp(self):
        upsert_property_definitions()
        self._hex_record = PubChemRecord(
            cid=8104,
            molecular_formula="C6H14O2",
            molecular_weight=118.17,
            isomeric_smiles="CCCCC(O)CO",
            inchikey="FHKSXSQHXQEMOK-UHFFFAOYSA-N",
            xlogp=0.8,
            tpsa=40.5,
            hbd=2.0,
            hba=2.0,
            cas_numbers=["6920-22-5"],
            pubmed_ids=["39805611", "39203006"],
        )

    def test_pubchem_only_writes_structure_and_descriptors(self):
        with mock.patch.object(
            pubchem_client, "fetch_compound", return_value=self._hex_record
        ):
            result = ingest_compound("1,2-Hexanediol", with_pubmed=False)

        compound = Compound.objects.get(canonical_inci="1,2-HEXANEDIOL")
        self.assertEqual(result.cid, 8104)
        self.assertTrue(compound.structure_resolvable)
        structure = CompoundStructure.objects.get(compound=compound)
        self.assertEqual(structure.inchikey, "FHKSXSQHXQEMOK-UHFFFAOYSA-N")
        self.assertEqual(compound.primary_cas, "6920-22-5")
        self.assertTrue(
            PropertyAssertion.objects.filter(
                compound=compound, property_def__key="logP", value_numeric=0.8
            ).exists()
        )
        self.assertEqual(result.descriptors_written, 5)

    def test_solvent_paper_classified_and_creates_relationship(self):
        [article] = pubmed_client.parse_efetch_xml(XML_SUGARCANE)
        with mock.patch.object(
            pubchem_client, "fetch_compound", return_value=self._hex_record
        ), mock.patch.object(
            pubmed_client, "esearch", return_value=["39203006"]
        ), mock.patch.object(
            pubmed_client, "efetch", return_value=[article]
        ):
            result = ingest_compound("1,2-Hexanediol", max_degree=1)

        compound = Compound.objects.get(canonical_inci="1,2-HEXANEDIOL")
        reference = LiteratureReference.objects.get(pmid="39203006")
        link = CompoundLiterature.objects.get(compound=compound, literature=reference)
        self.assertEqual(
            link.relevance_category, RelevanceCategory.PRESERVATION_PERFORMANCE
        )
        self.assertEqual(link.role_in_paper, RoleInPaper.SOLVENT)
        self.assertEqual(link.relationship_degree, 0)

        self.assertIn("PLANT EXTRACTS", result.related_compounds)
        plant = Compound.objects.get(canonical_inci="PLANT EXTRACTS")
        self.assertTrue(
            CompoundRelationship.objects.filter(
                compound_a=compound, compound_b=plant
            ).exists()
        )
        # Umbrella term filtered out.
        self.assertNotIn("COSMETICS", result.related_compounds)

    def test_subject_paper_classified_as_side_effect_family(self):
        [article] = pubmed_client.parse_efetch_xml(XML_HEXANEDIOL)
        with mock.patch.object(
            pubchem_client, "fetch_compound", return_value=self._hex_record
        ), mock.patch.object(
            pubmed_client, "esearch", return_value=["39805611"]
        ), mock.patch.object(
            pubmed_client, "efetch", return_value=[article]
        ):
            ingest_compound("1,2-Hexanediol", max_degree=1)

        compound = Compound.objects.get(canonical_inci="1,2-HEXANEDIOL")
        link = CompoundLiterature.objects.get(
            compound=compound, literature__pmid="39805611"
        )
        self.assertEqual(link.role_in_paper, RoleInPaper.SUBJECT)
        self.assertIn(
            link.relevance_category,
            {
                RelevanceCategory.SENSITIZATION,
                RelevanceCategory.IRRITATION,
                RelevanceCategory.SIDE_EFFECT,
                RelevanceCategory.SAFETY_PROFILE,
            },
        )

    def test_network_failure_degrades_gracefully(self):
        with mock.patch.object(
            pubchem_client, "fetch_compound", side_effect=RuntimeError("boom")
        ), mock.patch.object(
            pubmed_client, "esearch", side_effect=RuntimeError("down")
        ):
            result = ingest_compound("1,2-Hexanediol", max_degree=1)

        # Compound still created; errors captured, no crash.
        self.assertTrue(
            Compound.objects.filter(canonical_inci="1,2-HEXANEDIOL").exists()
        )
        self.assertTrue(result.errors)
