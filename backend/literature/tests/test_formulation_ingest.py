from django.test import TestCase

from literature.ingestion.formulation_ingest import parse_inci_list, resolve_compound
from core.models import Compound, FormulationIngredient
from core.models.product import Product
from literature.seeds.loader import upsert_property_definitions


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
