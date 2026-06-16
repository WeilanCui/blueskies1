from types import SimpleNamespace
from unittest import mock

from django.test import TestCase

from core.models import (
    Compound,
    DiscoveryReason,
    DiscoveryTargetStatus,
    EnrichmentStatus,
    Formulation,
    FormulationIngredient,
    LiteratureDiscoveryTarget,
    PRODUCT_FORMULATION_DISCOVERY_PRIORITY,
)
from literature.discovery import (
    LiteratureDiscoveryRunner,
    candidate_compounds_for_literature,
    enqueue_literature_discovery_for_compound,
)
from literature.ingestion.formulation_ingest import create_formulation, resolve_compound
from literature.seeds.loader import upsert_property_definitions


class EnqueueLiteratureDiscoveryTests(TestCase):
    def setUp(self):
        upsert_property_definitions()

    def test_resolve_compound_enqueues_new_compound_from_product(self):
        compound, status = resolve_compound("Phenoxyethanol", from_product=True)

        self.assertEqual(status, "unmatched")
        target = LiteratureDiscoveryTarget.objects.get(compound=compound)
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

        resolve_compound("Glycerin", from_product=True)

        low_priority.refresh_from_db()
        self.assertEqual(low_priority.priority, PRODUCT_FORMULATION_DISCOVERY_PRIORITY)
        self.assertEqual(low_priority.triggered_by, "formulation_ingest")
        self.assertEqual(LiteratureDiscoveryTarget.objects.count(), 1)

    def test_create_formulation_enqueues_all_ingredients(self):
        create_formulation("Test Serum", "Water, Retinol", brand="Blueskies")

        targets = LiteratureDiscoveryTarget.objects.filter(
            triggered_by="formulation_ingest",
        )
        self.assertEqual(targets.count(), 2)
        self.assertTrue(
            all(t.priority == PRODUCT_FORMULATION_DISCOVERY_PRIORITY for t in targets)
        )

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
