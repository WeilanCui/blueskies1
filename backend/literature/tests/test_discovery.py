from io import StringIO
from types import SimpleNamespace
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from core.models import (
    Compound,
    DiscoveryReason,
    DiscoveryTargetStatus,
    EnrichmentStatus,
    LiteratureDiscoveryEvent,
    LiteratureDiscoveryEventStatus,
    LiteratureDiscoveryEventType,
    Formulation,
    FormulationIngredient,
    LiteratureDiscoveryTarget,
    LiteratureDiscoveryTargetType,
    PRODUCT_FORMULATION_DISCOVERY_PRIORITY,
)
from literature.discovery import (
    LiteratureDiscoveryRunner,
    candidate_compounds_for_literature,
    dispatch_pending_literature_discovery_events,
    emit_literature_discovery_event,
    enqueue_literature_discovery_for_compound,
)
from literature.ingestion.formulation_ingest import create_formulation, resolve_compound
from literature.seeds.loader import upsert_property_definitions


class EnqueueLiteratureDiscoveryTests(TestCase):
    def setUp(self):
        upsert_property_definitions()

    def test_resolve_compound_enqueues_new_compound_from_product(self):
        with self.captureOnCommitCallbacks(execute=True):
            compound, status = resolve_compound("Phenoxyethanol", from_product=True)

        self.assertEqual(status, "unmatched")
        event = LiteratureDiscoveryEvent.objects.get(compound=compound)
        self.assertEqual(
            event.event_type,
            LiteratureDiscoveryEventType.COMPOUND_CREATED_FROM_FORMULATION,
        )
        self.assertEqual(event.status, LiteratureDiscoveryEventStatus.PROCESSED)
        target = LiteratureDiscoveryTarget.objects.get(compound=compound)
        self.assertEqual(target.target_type, LiteratureDiscoveryTargetType.COMPOUND)
        self.assertEqual(target.search_label, "Phenoxyethanol")
        self.assertEqual(target.status, DiscoveryTargetStatus.PENDING)
        self.assertEqual(target.reason, DiscoveryReason.NEW_COMPOUND)
        self.assertEqual(target.priority, PRODUCT_FORMULATION_DISCOVERY_PRIORITY)
        self.assertEqual(target.triggered_by, "formulation_ingest")

    def test_resolve_compound_without_product_context_does_not_enqueue(self):
        compound, status = resolve_compound("Phenoxyethanol")

        self.assertEqual(status, "unmatched")
        self.assertFalse(
            LiteratureDiscoveryTarget.objects.filter(compound=compound).exists()
        )

    def test_resolve_compound_bumps_priority_for_existing_compound(self):
        compound = Compound.objects.create(
            canonical_inci="GLYCERIN",
            display_name="Glycerin",
        )
        low_priority = LiteratureDiscoveryTarget.objects.create(
            compound=compound,
            reason=DiscoveryReason.NEW_COMPOUND,
            priority=0,
            triggered_by="ingest_compound",
        )

        with self.captureOnCommitCallbacks(execute=True):
            resolve_compound("Glycerin", from_product=True)

        low_priority.refresh_from_db()
        self.assertEqual(low_priority.priority, PRODUCT_FORMULATION_DISCOVERY_PRIORITY)
        self.assertEqual(low_priority.triggered_by, "formulation_ingest")
        self.assertEqual(LiteratureDiscoveryTarget.objects.count(), 1)

    def test_create_formulation_enqueues_all_ingredients(self):
        with self.captureOnCommitCallbacks(execute=True):
            create_formulation("Test Serum", "Water, Retinol", brand="Blueskies")

        targets = LiteratureDiscoveryTarget.objects.filter(
            triggered_by="formulation_ingest",
        )
        self.assertEqual(targets.count(), 2)
        self.assertTrue(
            all(t.priority == PRODUCT_FORMULATION_DISCOVERY_PRIORITY for t in targets)
        )
        self.assertEqual(LiteratureDiscoveryEvent.objects.count(), 2)

    def test_resolve_compound_skips_queue_when_disabled(self):
        compound, status = resolve_compound(
            "Phenoxyethanol",
            from_product=True,
            queue_discovery=False,
        )

        self.assertEqual(status, "unmatched")
        self.assertFalse(
            LiteratureDiscoveryTarget.objects.filter(compound=compound).exists()
        )
        self.assertFalse(LiteratureDiscoveryEvent.objects.exists())

    def test_reenqueue_while_pending_bumps_priority(self):
        compound = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
        )

        first, created_first = enqueue_literature_discovery_for_compound(
            compound,
            DiscoveryReason.NEW_COMPOUND,
            triggered_by="ingest_compound",
        )
        second, created_second = enqueue_literature_discovery_for_compound(
            compound,
            DiscoveryReason.NEW_COMPOUND,
            triggered_by="formulation_ingest",
        )

        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(LiteratureDiscoveryTarget.objects.count(), 1)
        second.refresh_from_db()
        self.assertEqual(second.priority, PRODUCT_FORMULATION_DISCOVERY_PRIORITY)

    def test_pending_event_dispatch_creates_work_item(self):
        compound = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
        )

        event, created = emit_literature_discovery_event(
            LiteratureDiscoveryEventType.COMPOUND_CREATED_FROM_FORMULATION,
            compound=compound,
            reason=DiscoveryReason.NEW_COMPOUND,
            triggered_by="formulation_ingest",
            source_ref="test:event",
        )

        self.assertTrue(created)
        self.assertEqual(event.status, LiteratureDiscoveryEventStatus.PENDING)
        self.assertFalse(LiteratureDiscoveryTarget.objects.exists())

        result = dispatch_pending_literature_discovery_events(limit=10)

        event.refresh_from_db()
        target = LiteratureDiscoveryTarget.objects.get(compound=compound)
        self.assertEqual(result["events_processed"], 1)
        self.assertEqual(result["targets_created"], 1)
        self.assertEqual(event.status, LiteratureDiscoveryEventStatus.PROCESSED)
        self.assertEqual(target.target_type, LiteratureDiscoveryTargetType.COMPOUND)
        self.assertEqual(target.search_label, "Retinol")

    def test_mixture_compound_event_creates_compound_work_item(self):
        with self.captureOnCommitCallbacks(execute=True):
            compound, status = resolve_compound("Retinol Complex", from_product=True)

        self.assertEqual(status, "unmatched")
        self.assertEqual(compound.entity_type, "mixture")
        event = LiteratureDiscoveryEvent.objects.get(compound=compound)
        target = LiteratureDiscoveryTarget.objects.get(compound=compound)
        self.assertEqual(
            event.event_type,
            LiteratureDiscoveryEventType.MIXTURE_CREATED_FROM_FORMULATION,
        )
        self.assertEqual(target.target_type, LiteratureDiscoveryTargetType.COMPOUND)
        self.assertEqual(target.reason, DiscoveryReason.NEW_MIXTURE)


class LiteratureDiscoveryRunnerTests(TestCase):
    def setUp(self):
        upsert_property_definitions()

    def test_runner_marks_target_completed_on_success(self):
        compound = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
        )
        target = LiteratureDiscoveryTarget.objects.create(
            compound=compound,
            reason=DiscoveryReason.NEW_COMPOUND,
            triggered_by="formulation_ingest",
            priority=PRODUCT_FORMULATION_DISCOVERY_PRIORITY,
        )

        def ingest(name, **kwargs):
            return SimpleNamespace(
                articles_linked=2,
                related_compounds=[],
                errors=[],
            )

        runner = LiteratureDiscoveryRunner(
            compound_limit=5,
            ingest_compound_func=ingest,
        )
        result = runner.run()

        target.refresh_from_db()
        self.assertEqual(result["targets_processed"], 1)
        self.assertEqual(target.status, DiscoveryTargetStatus.COMPLETED)
        self.assertIsNotNone(target.completed_at)

    def test_runner_retries_then_skips_after_max_attempts(self):
        compound = Compound.objects.create(
            canonical_inci="RETINAL",
            display_name="Retinal",
        )
        target = LiteratureDiscoveryTarget.objects.create(
            compound=compound,
            reason=DiscoveryReason.NEW_COMPOUND,
            triggered_by="formulation_ingest",
            priority=PRODUCT_FORMULATION_DISCOVERY_PRIORITY,
        )

        def ingest(name, **kwargs):
            return SimpleNamespace(
                articles_linked=0,
                related_compounds=[],
                errors=["pubmed:429 Too Many Requests"],
            )

        runner = LiteratureDiscoveryRunner(
            compound_limit=5,
            max_attempts=3,
            ingest_compound_func=ingest,
        )

        for _ in range(3):
            runner.run()

        target.refresh_from_db()
        self.assertEqual(target.attempt_count, 3)
        self.assertEqual(target.status, DiscoveryTargetStatus.SKIPPED)
        self.assertIn("429", target.last_error)

    def test_runner_records_failures_when_ingest_raises(self):
        compound = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
        )
        target = LiteratureDiscoveryTarget.objects.create(
            compound=compound,
            reason=DiscoveryReason.NEW_COMPOUND,
            triggered_by="formulation_ingest",
            priority=PRODUCT_FORMULATION_DISCOVERY_PRIORITY,
        )

        def ingest(name, **kwargs):
            raise RuntimeError("pubchem timeout")

        runner = LiteratureDiscoveryRunner(
            compound_limit=5,
            max_attempts=3,
            ingest_compound_func=ingest,
        )

        with self.assertRaises(RuntimeError):
            runner.process_target(target)

        target.refresh_from_db()
        self.assertEqual(target.attempt_count, 1)
        self.assertEqual(target.status, DiscoveryTargetStatus.PENDING)
        self.assertIn("pubchem timeout", target.last_error)

        for _ in range(2):
            with self.assertRaises(RuntimeError):
                runner.process_target(target)

        target.refresh_from_db()
        self.assertEqual(target.attempt_count, 3)
        self.assertEqual(target.status, DiscoveryTargetStatus.SKIPPED)

    def test_runner_skips_ingest_compound_only_pending_targets(self):
        noise = Compound.objects.create(
            canonical_inci="ORGANOPHOSPHORUS COMPOUNDS",
            display_name="Organophosphorus Compounds",
        )
        LiteratureDiscoveryTarget.objects.create(
            compound=noise,
            reason=DiscoveryReason.NEW_COMPOUND,
            triggered_by="ingest_compound",
        )
        product_compound = Compound.objects.create(
            canonical_inci="NIACINAMIDE",
            display_name="Niacinamide",
        )
        product_target = LiteratureDiscoveryTarget.objects.create(
            compound=product_compound,
            reason=DiscoveryReason.NEW_COMPOUND,
            priority=PRODUCT_FORMULATION_DISCOVERY_PRIORITY,
            triggered_by="formulation_ingest",
        )

        processed: list[str] = []

        def ingest(name, **kwargs):
            processed.append(name)
            return SimpleNamespace(
                articles_linked=1,
                related_compounds=[],
                errors=[],
            )

        runner = LiteratureDiscoveryRunner(
            compound_limit=5,
            product_targets_only=True,
            ingest_compound_func=ingest,
        )
        result = runner.run()

        self.assertEqual(result["targets_processed"], 1)
        self.assertEqual(processed, ["Niacinamide"])
        product_target.refresh_from_db()
        noise_target = LiteratureDiscoveryTarget.objects.get(compound=noise)
        self.assertEqual(product_target.status, DiscoveryTargetStatus.COMPLETED)
        self.assertEqual(noise_target.status, DiscoveryTargetStatus.PENDING)

    def test_runner_product_only_false_processes_ingest_compound_targets(self):
        compound = Compound.objects.create(
            canonical_inci="ORGANOPHOSPHORUS COMPOUNDS",
            display_name="Organophosphorus Compounds",
        )
        target = LiteratureDiscoveryTarget.objects.create(
            compound=compound,
            reason=DiscoveryReason.NEW_COMPOUND,
            triggered_by="ingest_compound",
        )

        runner = LiteratureDiscoveryRunner(
            compound_limit=5,
            product_targets_only=False,
            ingest_compound_func=lambda name, **kwargs: SimpleNamespace(
                articles_linked=0,
                related_compounds=[],
                errors=[],
            ),
        )
        result = runner.run()

        self.assertEqual(result["targets_processed"], 1)
        target.refresh_from_db()
        self.assertEqual(target.status, DiscoveryTargetStatus.COMPLETED)

    def test_runner_skips_formulation_targets_until_processor_exists(self):
        from core.models import Product
        from core.models.brand import Brand

        brand = Brand.objects.create(name="Test Brand")
        product_obj = Product.objects.create(brand=brand, name="Test Serum")
        formulation = Formulation.objects.create(
            product=product_obj,
            raw_inci_text="Water, Glycerin",
        )
        target = LiteratureDiscoveryTarget.objects.create(
            target_type=LiteratureDiscoveryTargetType.FORMULATION,
            formulation=formulation,
            reason=DiscoveryReason.NEW_COMPOUND,
            triggered_by="formulation_ingest",
            priority=PRODUCT_FORMULATION_DISCOVERY_PRIORITY,
        )

        runner = LiteratureDiscoveryRunner(
            compound_limit=5,
            ingest_compound_func=lambda name, **kwargs: SimpleNamespace(
                articles_linked=0,
                related_compounds=[],
                errors=[],
            ),
        )
        result = runner.run()

        target.refresh_from_db()
        self.assertEqual(result["targets_processed"], 1)
        self.assertEqual(result["compounds_processed"], 0)
        self.assertEqual(target.status, DiscoveryTargetStatus.SKIPPED)
        self.assertIn("No literature discovery processor", target.last_error)

    def test_runner_backfills_pending_formulation_compounds_when_queue_empty(self):
        from core.models import Product
        from core.models.brand import Brand

        compound = Compound.objects.create(
            canonical_inci="PANTHENOL",
            display_name="Panthenol",
            enrichment_status=EnrichmentStatus.PENDING,
        )
        brand = Brand.objects.create(name="Test Brand")
        product_obj = Product.objects.create(brand=brand, name="Test Serum")
        formulation = Formulation.objects.create(
            product=product_obj,
            raw_inci_text="Panthenol",
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=1,
            raw_text="Panthenol",
            compound=compound,
        )

        processed: list[str] = []

        def ingest(name, **kwargs):
            processed.append(name)
            return SimpleNamespace(
                articles_linked=1,
                related_compounds=[],
                errors=[],
            )

        runner = LiteratureDiscoveryRunner(
            compound_limit=3,
            backfill_limit=None,
            backfill_formulation_only=True,
            ingest_compound_func=ingest,
        )
        result = runner.run()

        self.assertEqual(result["targets_processed"], 0)
        self.assertEqual(result["backfill_processed"], 1)
        self.assertEqual(processed, ["Panthenol"])
        target = LiteratureDiscoveryTarget.objects.get(compound=compound)
        self.assertEqual(target.status, DiscoveryTargetStatus.COMPLETED)
        self.assertEqual(target.source_ref, f"literature_backfill:{compound.pk}")
        self.assertEqual(target.triggered_by, "formulation_ingest")

    def test_enqueue_pending_compounds_for_literature(self):
        from literature.discovery import enqueue_pending_compounds_for_literature

        compound = Compound.objects.create(
            canonical_inci="ALLANTOIN",
            display_name="Allantoin",
            enrichment_status=EnrichmentStatus.PENDING,
        )
        from core.models import Product
        from core.models.brand import Brand

        brand = Brand.objects.create(name="Test Brand")
        product_obj = Product.objects.create(brand=brand, name="Test Cream")
        formulation = Formulation.objects.create(
            product=product_obj,
            raw_inci_text="Allantoin",
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=1,
            raw_text="Allantoin",
            compound=compound,
        )

        enqueued = enqueue_pending_compounds_for_literature(5)
        self.assertEqual(enqueued, 1)
        target = LiteratureDiscoveryTarget.objects.get(compound=compound)
        self.assertEqual(target.status, DiscoveryTargetStatus.PENDING)
        self.assertEqual(target.triggered_by, "formulation_ingest")

    def test_requeue_stale_running_targets(self):
        from datetime import timedelta

        from django.utils import timezone

        from literature.discovery import requeue_stale_running_targets

        compound = Compound.objects.create(
            canonical_inci="STALEINE",
            display_name="Staleine",
        )
        stale = LiteratureDiscoveryTarget.objects.create(
            compound=compound,
            reason=DiscoveryReason.NEW_COMPOUND,
            status=DiscoveryTargetStatus.RUNNING,
            triggered_by="formulation_ingest",
            last_run_at=timezone.now() - timedelta(hours=2),
        )
        fresh = LiteratureDiscoveryTarget.objects.create(
            compound=Compound.objects.create(
                canonical_inci="FRESHINE",
                display_name="Freshine",
            ),
            reason=DiscoveryReason.NEW_COMPOUND,
            status=DiscoveryTargetStatus.RUNNING,
            triggered_by="formulation_ingest",
            last_run_at=timezone.now(),
        )

        requeued = requeue_stale_running_targets(stale_after_seconds=3600)

        self.assertEqual(requeued, 1)
        stale.refresh_from_db()
        fresh.refresh_from_db()
        self.assertEqual(stale.status, DiscoveryTargetStatus.PENDING)
        self.assertEqual(fresh.status, DiscoveryTargetStatus.RUNNING)

    def test_enqueue_recovers_stale_running_target_for_compound(self):
        from datetime import timedelta

        from django.utils import timezone

        compound = Compound.objects.create(
            canonical_inci="RECOVERINE",
            display_name="Recoverine",
        )
        target = LiteratureDiscoveryTarget.objects.create(
            compound=compound,
            reason=DiscoveryReason.NEW_COMPOUND,
            status=DiscoveryTargetStatus.RUNNING,
            triggered_by="formulation_ingest",
            priority=0,
            last_run_at=timezone.now() - timedelta(hours=2),
        )

        _, created = enqueue_literature_discovery_for_compound(
            compound,
            DiscoveryReason.NEW_COMPOUND,
            triggered_by="formulation_ingest",
            priority=PRODUCT_FORMULATION_DISCOVERY_PRIORITY,
        )

        self.assertFalse(created)
        target.refresh_from_db()
        self.assertEqual(target.status, DiscoveryTargetStatus.PENDING)
        self.assertEqual(target.priority, PRODUCT_FORMULATION_DISCOVERY_PRIORITY)

    def test_candidate_compounds_excludes_active_queue_targets(self):
        queued = Compound.objects.create(
            canonical_inci="NIACINAMIDE",
            display_name="Niacinamide",
            enrichment_status=EnrichmentStatus.PENDING,
        )
        LiteratureDiscoveryTarget.objects.create(
            compound=queued,
            reason=DiscoveryReason.NEW_COMPOUND,
        )
        backfill = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
            enrichment_status=EnrichmentStatus.PENDING,
        )
        Compound.objects.create(
            canonical_inci="AQUA",
            display_name="Water",
            enrichment_status=EnrichmentStatus.PENDING,
        )

        candidates = list(candidate_compounds_for_literature(limit=10))

        self.assertEqual(candidates, [backfill])

    def test_candidate_compounds_prefers_formulation_ingredients(self):
        orphan = Compound.objects.create(
            canonical_inci="ORPHANINE",
            display_name="Orphanine",
            enrichment_status=EnrichmentStatus.PENDING,
        )
        on_product = Compound.objects.create(
            canonical_inci="SERUMIDE",
            display_name="Serumide",
            enrichment_status=EnrichmentStatus.PENDING,
        )
        from core.models import Product
        from core.models.brand import Brand

        brand = Brand.objects.create(name="Test Brand")
        product_obj = Product.objects.create(brand=brand, name="Test Serum")
        formulation = Formulation.objects.create(
            product=product_obj,
            raw_inci_text="Serumide",
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=1,
            raw_text="Serumide",
            compound=on_product,
        )

        candidates = list(candidate_compounds_for_literature(limit=2))

        self.assertEqual([c.pk for c in candidates], [on_product.pk, orphan.pk])


class LiteratureDiscoveryCommandTests(TestCase):
    def setUp(self):
        upsert_property_definitions()

    @mock.patch("literature.ingestion.ingest_compound")
    def test_command_dispatches_events_and_executes_targets(self, mock_ingest):
        mock_ingest.return_value = SimpleNamespace(
            articles_linked=1,
            related_compounds=[],
            errors=[],
        )
        compound = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
        )
        event, _ = emit_literature_discovery_event(
            LiteratureDiscoveryEventType.COMPOUND_CREATED_FROM_FORMULATION,
            compound=compound,
            reason=DiscoveryReason.NEW_COMPOUND,
            triggered_by="formulation_ingest",
            source_ref="test:command",
        )

        self.assertEqual(event.status, LiteratureDiscoveryEventStatus.PENDING)
        self.assertFalse(LiteratureDiscoveryTarget.objects.exists())

        out = StringIO()
        call_command(
            "literature_discovery",
            limit=5,
            no_backfill=True,
            execute_now=True,
            stdout=out,
        )

        event.refresh_from_db()
        target = LiteratureDiscoveryTarget.objects.get(compound=compound)
        self.assertEqual(event.status, LiteratureDiscoveryEventStatus.PROCESSED)
        self.assertEqual(target.status, DiscoveryTargetStatus.COMPLETED)
        mock_ingest.assert_called_once_with(
            "Retinol",
            with_pubmed=True,
            max_articles=5,
            max_related=3,
            enrich=False,
            asserted_by="literature_discovery_runner",
        )
        self.assertIn("1 events dispatched", out.getvalue())

    @mock.patch(
        "literature.management.commands.literature_discovery."
        "drain_literature_discovery_queue.apply_async"
    )
    def test_command_schedules_celery_drainer_without_executing(self, mock_apply_async):
        compound = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
            enrichment_status=EnrichmentStatus.PENDING,
        )
        from core.models import Product
        from core.models.brand import Brand

        brand = Brand.objects.create(name="Test Brand")
        product_obj = Product.objects.create(brand=brand, name="Test Serum")
        formulation = Formulation.objects.create(
            product=product_obj,
            raw_inci_text="Retinol",
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=1,
            raw_text="Retinol",
            compound=compound,
        )

        out = StringIO()
        call_command(
            "literature_discovery",
            enqueue=5,
            queue_celery=True,
            drain_countdown=15,
            stdout=out,
        )

        target = LiteratureDiscoveryTarget.objects.get(compound=compound)
        self.assertEqual(target.status, DiscoveryTargetStatus.PENDING)
        mock_apply_async.assert_called_once_with(
            kwargs={
                "compound_limit": 25,
                "event_limit": 100,
                "drain_countdown": 15,
                "max_articles": 5,
                "max_related": 3,
                "enrich": False,
                "product_targets_only": True,
            }
        )
        self.assertIn("Scheduled literature discovery drainer", out.getvalue())

    def test_command_without_execution_only_seeds_targets(self):
        out = StringIO()
        call_command(
            "literature_discovery",
            stdout=out,
        )

        self.assertIn("No execution requested", out.getvalue())
