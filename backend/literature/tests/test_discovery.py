from types import SimpleNamespace
from unittest import mock

from django.test import TestCase

from core.models import (
    Compound,
    DiscoveryReason,
    DiscoveryTargetStatus,
    EnrichmentStatus,
    LiteratureDiscoveryTarget,
)
from literature.discovery import (
    LiteratureDiscoveryRunner,
    candidate_compounds_for_literature,
    enqueue_literature_discovery_for_compound,
)
from literature.ingestion.formulation_ingest import resolve_compound
from literature.seeds.loader import upsert_property_definitions


class EnqueueLiteratureDiscoveryTests(TestCase):
    def setUp(self):
        upsert_property_definitions()

    def test_resolve_compound_enqueues_new_compound(self):
        compound, status = resolve_compound("Phenoxyethanol")

        self.assertEqual(status, "unmatched")
        target = LiteratureDiscoveryTarget.objects.get(compound=compound)
        self.assertEqual(target.status, DiscoveryTargetStatus.PENDING)
        self.assertEqual(target.reason, DiscoveryReason.NEW_COMPOUND)

    def test_reenqueue_while_pending_is_idempotent(self):
        compound = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
        )

        first, created_first = enqueue_literature_discovery_for_compound(
            compound,
            DiscoveryReason.NEW_COMPOUND,
        )
        second, created_second = enqueue_literature_discovery_for_compound(
            compound,
            DiscoveryReason.RETRY,
        )

        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(LiteratureDiscoveryTarget.objects.count(), 1)


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
