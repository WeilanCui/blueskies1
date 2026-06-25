from unittest import mock

from django.test import TestCase

from core.models import Compound, FormulationIngredient
from core.models.product import Product
from literature.models import LiteratureDiscoveryTarget
from literature.ingestion.formulation_ingest import (
    ingest_formulation,
    parse_inci_list,
    resolve_compound,
)
from literature.seeds.loader import upsert_property_definitions
from types import SimpleNamespace


class ParseInciListTests(TestCase):
    def test_splits_comma_separated_values(self):
        text = "Water, Glycerin, Niacinamide"
        self.assertEqual(parse_inci_list(text), ["Water", "Glycerin", "Niacinamide"])

    def test_splits_newlines_and_deduplicates(self):
        text = "Water\nGlycerin\nWater"
        self.assertEqual(parse_inci_list(text), ["Water", "Glycerin"])

    def test_strips_parenthetical_aliases(self):
        text = "Aqua (Water), Tocopherol (Vitamin E)"
        self.assertEqual(parse_inci_list(text), ["Aqua", "Tocopherol"])


class ResolveCompoundTests(TestCase):
    def setUp(self):
        upsert_property_definitions()

    def test_creates_compound_when_missing(self):
        compound, status = resolve_compound("Phenoxyethanol")
        self.assertEqual(status, "unmatched")
        self.assertEqual(compound.canonical_inci, "PHENOXYETHANOL")

    def test_matches_existing_compound(self):
        existing = Compound.objects.create(
            canonical_inci="GLYCERIN",
            display_name="Glycerin",
        )
        compound, status = resolve_compound("Glycerin")
        self.assertEqual(status, "matched")
        self.assertEqual(compound.pk, existing.pk)


class CreateFormulationTests(TestCase):
    def setUp(self):
        upsert_property_definitions()

    def test_persists_formulation_rows(self):
        from literature.ingestion.formulation_ingest import create_formulation

        formulation = create_formulation(
            "Test Serum",
            "Water, Glycerin",
            brand="Blueskies",
        )
        self.assertEqual(formulation.name, "Test Serum")
        self.assertEqual(formulation.brand, "Blueskies")
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(formulation.product.name, "Test Serum")
        self.assertEqual(formulation.product.brand.name, "Blueskies")
        self.assertEqual(FormulationIngredient.objects.filter(formulation=formulation).count(), 2)


class IngestFormulationTests(TestCase):
    def setUp(self):
        upsert_property_definitions()

    @mock.patch("literature.ingestion.formulation_ingest.ingest_compound")
    @mock.patch("literature.ingestion.formulation_ingest.ingest_inci_ingredient")
    def test_sync_ingest_does_not_enqueue_discovery_targets(
        self,
        mock_ingest_inci,
        mock_ingest_compound,
    ):
        mock_ingest_inci.return_value = SimpleNamespace(
            properties_written=1,
            errors=[],
        )
        mock_ingest_compound.return_value = SimpleNamespace(
            descriptors_written=2,
            articles_linked=3,
            errors=[],
        )

        ingest_formulation("Test Serum", "Retinol, Glycerin", brand="Blueskies")

        self.assertFalse(LiteratureDiscoveryTarget.objects.exists())
        self.assertEqual(mock_ingest_compound.call_count, 2)
        for call in mock_ingest_inci.call_args_list:
            self.assertFalse(call.kwargs.get("queue_discovery", True))
