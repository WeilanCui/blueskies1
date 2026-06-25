from types import SimpleNamespace
from unittest import mock

from django.test import TestCase

from core.models import (
    Compound,
    Formulation,
    FormulationIngredient,
)
from core.tasks import daily_literature_discovery_task, enrich_formulation_ingredients
from literature.models import (
    DiscoveryReason,
    DiscoveryTargetStatus,
    LiteratureDiscoveryTarget,
    PRODUCT_FORMULATION_DISCOVERY_PRIORITY,
)
<<<<<<< HEAD
from core.tasks import (
    daily_literature_discovery_task,
    drain_literature_discovery_queue,
    enrich_formulation_ingredients,
)
=======
>>>>>>> main
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

    @mock.patch("core.tasks.drain_literature_discovery_queue.apply_async")
    @mock.patch("literature.discovery.pending_literature_discovery_target_count")
    @mock.patch("literature.discovery.enqueue_pending_compounds_for_literature")
    def test_daily_task_seeds_targets_and_schedules_drain(
        self,
        mock_enqueue,
        mock_pending_count,
        mock_apply_async,
    ):
        mock_enqueue.return_value = 7
        mock_pending_count.return_value = 42

        result = daily_literature_discovery_task(
            compound_limit=10,
            max_articles=3,
        )

        mock_enqueue.assert_called_once_with(10, formulation_only=True)
        mock_pending_count.assert_called_once_with()
        mock_apply_async.assert_called_once_with(
            kwargs={
                "compound_limit": 10,
                "event_limit": 100,
                "drain_countdown": 60,
                "max_articles": 3,
                "max_related": 3,
                "enrich": False,
            }
        )
        self.assertEqual(result["targets_seeded"], 7)
        self.assertEqual(result["pending_targets"], 42)
        self.assertTrue(result["drain_scheduled"])

    @mock.patch("literature.discovery.LiteratureDiscoveryRunner")
    @mock.patch("literature.discovery.dispatch_pending_literature_discovery_events")
    @mock.patch("literature.discovery.pending_literature_discovery_event_count")
    @mock.patch("literature.discovery.pending_literature_discovery_target_count")
    def test_drain_task_delegates_to_runner_without_backfill(
        self,
        mock_pending_count,
        mock_pending_event_count,
        mock_dispatch_events,
        mock_runner_cls,
    ):
        mock_dispatch_events.return_value = {
            "events_processed": 0,
            "events_failed": 0,
            "targets_created": 0,
            "events": [],
        }
        mock_pending_count.return_value = 0
        mock_pending_event_count.return_value = 0
        mock_runner_cls.return_value.run.return_value = {
            "targets_processed": 2,
            "backfill_processed": 0,
            "compounds_processed": 2,
            "targets": [],
            "backfill": [],
            "errors": [],
        }

        result = drain_literature_discovery_queue(
            compound_limit=10,
            max_articles=3,
        )

        mock_dispatch_events.assert_called_once_with(limit=100)
        mock_runner_cls.assert_called_once_with(
            compound_limit=10,
            backfill_limit=0,
            max_articles=3,
            max_related=3,
            enrich=False,
            product_targets_only=True,
        )
        self.assertEqual(result["targets_processed"], 2)
        self.assertFalse(result["rescheduled"])

    @mock.patch("core.tasks.drain_literature_discovery_queue.apply_async")
    @mock.patch("literature.discovery.LiteratureDiscoveryRunner")
    @mock.patch("literature.discovery.dispatch_pending_literature_discovery_events")
    @mock.patch("literature.discovery.pending_literature_discovery_event_count")
    @mock.patch("literature.discovery.pending_literature_discovery_target_count")
    def test_drain_reschedules_when_pending_events_remain(
        self,
        mock_pending_count,
        mock_pending_event_count,
        mock_dispatch_events,
        mock_runner_cls,
        mock_apply_async,
    ):
        mock_dispatch_events.return_value = {
            "events_processed": 10,
            "events_failed": 0,
            "targets_created": 10,
            "events": [],
        }
        mock_pending_count.return_value = 0
        mock_pending_event_count.return_value = 3
        mock_runner_cls.return_value.run.return_value = {
            "targets_processed": 10,
            "backfill_processed": 0,
            "compounds_processed": 10,
            "targets": [],
            "backfill": [],
            "errors": [],
        }

        result = drain_literature_discovery_queue(
            compound_limit=25,
            event_limit=10,
            drain_countdown=20,
        )

        self.assertEqual(result["pending_remaining"], 0)
        self.assertEqual(result["pending_events_remaining"], 3)
        self.assertTrue(result["rescheduled"])
        mock_apply_async.assert_called_once_with(
            kwargs={
                "compound_limit": 25,
                "event_limit": 10,
                "drain_countdown": 20,
                "max_articles": 5,
                "max_related": 3,
                "enrich": False,
                "product_targets_only": True,
            },
            countdown=20,
        )

    @mock.patch("literature.ingestion.ingest_compound")
    @mock.patch("core.tasks.drain_literature_discovery_queue.apply_async")
    def test_drain_processes_pending_queue_targets(self, mock_apply_async, mock_ingest):
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

        result = drain_literature_discovery_queue(
            compound_limit=5,
            max_articles=3,
        )

        self.assertEqual(result["targets_processed"], 1)
        self.assertEqual(result["backfill_processed"], 0)
        self.assertEqual(result["pending_remaining"], 0)
        self.assertFalse(result["rescheduled"])
        mock_apply_async.assert_not_called()
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

    @mock.patch("literature.ingestion.ingest_compound")
    @mock.patch("core.tasks.drain_literature_discovery_queue.apply_async")
    def test_drain_reschedules_when_pending_targets_remain(
        self,
        mock_apply_async,
        mock_ingest,
    ):
        mock_ingest.return_value = SimpleNamespace(
            articles_linked=1,
            related_compounds=[],
            errors=[],
        )
        first = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
        )
        second = Compound.objects.create(
            canonical_inci="NIACINAMIDE",
            display_name="Niacinamide",
        )
        for compound in (first, second):
            LiteratureDiscoveryTarget.objects.create(
                compound=compound,
                reason=DiscoveryReason.NEW_COMPOUND,
                triggered_by="formulation_ingest",
                priority=PRODUCT_FORMULATION_DISCOVERY_PRIORITY,
            )

        result = drain_literature_discovery_queue(
            compound_limit=1,
            drain_countdown=30,
        )

        self.assertEqual(result["targets_processed"], 1)
        self.assertEqual(result["pending_remaining"], 1)
        self.assertTrue(result["rescheduled"])
        mock_apply_async.assert_called_once_with(
            kwargs={
                "compound_limit": 1,
                "event_limit": 100,
                "drain_countdown": 30,
                "max_articles": 5,
                "max_related": 3,
                "enrich": False,
                "product_targets_only": True,
            },
            countdown=30,
        )
