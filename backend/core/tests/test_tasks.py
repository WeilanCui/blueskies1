from unittest import mock

from django.test import TestCase

from core.models import Formulation, FormulationIngredient
from core.tasks import enrich_formulation_ingredients
from literature.seeds.loader import upsert_property_definitions


class EnrichFormulationIngredientsTaskTests(TestCase):
    def setUp(self):
        upsert_property_definitions()

    @mock.patch("literature.ingestion.inci_ingest.ingest_inci_ingredient")
    def test_creates_formulation_when_payload_is_provided(self, mock_ingest):
        result = enrich_formulation_ingredients(
            999,
            product_name="Barrier Cream",
            raw_inci_text="Water, Glycerin",
            brand="Blueskies",
        )

        self.assertTrue(result["created"])
        self.assertNotEqual(result["formulation_id"], 999)
        self.assertEqual(result["success_count"], 2)
        self.assertEqual(mock_ingest.call_count, 2)

        formulation = Formulation.objects.get(pk=result["formulation_id"])
        self.assertEqual(formulation.product.name, "Barrier Cream")
        self.assertEqual(formulation.product.brand.name, "Blueskies")
        self.assertEqual(
            list(
                FormulationIngredient.objects.filter(formulation=formulation)
                .order_by("position")
                .values_list("raw_text", flat=True)
            ),
            ["Water", "Glycerin"],
        )

    def test_missing_formulation_without_payload_returns_clear_error(self):
        result = enrich_formulation_ingredients(999)

        self.assertFalse(result["created"])
        self.assertEqual(result["formulation_id"], 999)
        self.assertIn("product_name", result["error"])
