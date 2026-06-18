from types import SimpleNamespace
from unittest import mock

from django.test import TestCase

from core.models import (
    Compound,
    DiscoveryReason,
    DiscoveryTargetStatus,
    Formulation,
    FormulationIngredient,
    LiteratureDiscoveryTarget,
    PRODUCT_FORMULATION_DISCOVERY_PRIORITY,
)
from core.tasks import daily_literature_discovery_task, enrich_formulation_ingredients
from literature.seeds.loader import upsert_property_definitions


class EnrichFormulationIngredientsTaskTests(TestCase):
    def setUp(self):
        upsert_property_definitions()

    @mock.patch("literature.ingestion.inci_ingest.ingest_inci_ingredient")
    def test_creates_formulation_when_payload_is_provided(self, mock_ingest):
        mock_ingest.return_value.errors = []

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

    @mock.patch("literature.ingestion.inci_ingest.ingest_inci_ingredient")
    def test_reuses_formulation_for_same_payload_on_retry(self, mock_ingest):
        mock_ingest.return_value.errors = []

        first = enrich_formulation_ingredients(
            999,
            product_name="Barrier Cream",
            raw_inci_text="Water, Glycerin",
            brand="Blueskies",
        )
        second = enrich_formulation_ingredients(
            999,
            product_name="Barrier Cream",
            raw_inci_text="Water, Glycerin",
            brand="Blueskies",
        )

        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(second["formulation_id"], first["formulation_id"])
        self.assertEqual(Formulation.objects.count(), 1)
        self.assertEqual(FormulationIngredient.objects.count(), 2)
        self.assertEqual(mock_ingest.call_count, 4)

    def test_missing_formulation_without_payload_returns_clear_error(self):
        result = enrich_formulation_ingredients(999)

        self.assertFalse(result["created"])
        self.assertEqual(result["formulation_id"], 999)
        self.assertIn("product_name", result["error"])


class DailyLiteratureDiscoveryTaskTests(TestCase):
    def setUp(self):
        upsert_property_definitions()

    @mock.patch("literature.discovery.LiteratureDiscoveryRunner")
    def test_delegates_to_runner(self, mock_runner_cls):
        mock_runner_cls.return_value.run.return_value = {
            "targets_processed": 2,
            "backfill_processed": 0,
            "compounds_processed": 2,
            "targets": [],
            "backfill": [],
            "errors": [],
        }

        result = daily_literature_discovery_task(
            compound_limit=10,
            max_articles=3,
        )

        mock_runner_cls.assert_called_once_with(
            compound_limit=10,
            backfill_limit=None,
            max_articles=3,
            max_related=3,
            enrich=False,
        )
        self.assertEqual(result["targets_processed"], 2)

    @mock.patch("literature.ingestion.ingest_compound")
    def test_processes_pending_queue_targets(self, mock_ingest):
        mock_ingest.return_value = SimpleNamespace(
            articles_linked=2,
            related_compounds=["RETINAL"],
            errors=[],
        )
        compound = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
        )
        LiteratureDiscoveryTarget.objects.create(
            compound=compound,
            reason=DiscoveryReason.NEW_COMPOUND,
            triggered_by="formulation_ingest",
            priority=PRODUCT_FORMULATION_DISCOVERY_PRIORITY,
        )

        result = daily_literature_discovery_task(
            compound_limit=5,
            max_articles=3,
        )

        self.assertEqual(result["targets_processed"], 1)
        self.assertEqual(result["backfill_processed"], 0)
        mock_ingest.assert_called_once_with(
            "Retinol",
            with_pubmed=True,
            max_articles=3,
            max_related=3,
            enrich=False,
            asserted_by="literature_discovery_runner",
        )
        target = LiteratureDiscoveryTarget.objects.get(compound=compound)
        self.assertEqual(target.status, DiscoveryTargetStatus.COMPLETED)
