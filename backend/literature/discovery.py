"""Reusable literature discovery orchestration for scheduled jobs and callers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from core.models import Compound, CompoundLiterature, EnrichmentStatus, FormulationIngredient
from core.models.literature_discovery_target import (
    ACTIVE_DISCOVERY_STATUSES,
    DEFAULT_DISCOVERY_PRIORITY,
    DEFAULT_MAX_DISCOVERY_ATTEMPTS,
    DiscoveryReason,
    DiscoveryTargetStatus,
    LiteratureDiscoveryTarget,
    PRODUCT_FORMULATION_DISCOVERY_PRIORITY,
)

logger = logging.getLogger(__name__)

DEFAULT_EXCLUDED_CANONICAL_INCI = ("AQUA", "WATER")

PRODUCT_DISCOVERY_TRIGGERED_BY = frozenset(
    {
        "formulation_ingest",
        "barcode_scan",
    }
)


def discovery_priority_for_triggered_by(triggered_by: str) -> int:
    if triggered_by in PRODUCT_DISCOVERY_TRIGGERED_BY:
        return PRODUCT_FORMULATION_DISCOVERY_PRIORITY
    return DEFAULT_DISCOVERY_PRIORITY


def enqueue_literature_discovery_for_compound(
    compound: Compound,
    reason: str,
    *,
    priority: int | None = None,
    source_ref: str = "",
    triggered_by: str = "",
) -> tuple[LiteratureDiscoveryTarget, bool]:
    """Queue compound-level literature discovery; idempotent while pending/running."""
    if priority is None:
        priority = discovery_priority_for_triggered_by(triggered_by)

    existing = LiteratureDiscoveryTarget.objects.filter(
        compound=compound,
        status__in=ACTIVE_DISCOVERY_STATUSES,
    ).first()
    if existing is not None:
        updates: dict[str, object] = {}
        if priority > existing.priority:
            updates["priority"] = priority
        if triggered_by and (
            not existing.triggered_by
            or triggered_by in PRODUCT_DISCOVERY_TRIGGERED_BY
        ):
            updates["triggered_by"] = triggered_by
        if source_ref:
            updates["source_ref"] = source_ref
        if updates:
            for field, value in updates.items():
                setattr(existing, field, value)
            existing.save(update_fields=[*updates.keys(), "updated_at"])
        return existing, False

    try:
        target = LiteratureDiscoveryTarget.objects.create(
            compound=compound,
            reason=reason,
            status=DiscoveryTargetStatus.PENDING,
            priority=priority,
            source_ref=source_ref,
            triggered_by=triggered_by,
        )
    except IntegrityError:
        existing = LiteratureDiscoveryTarget.objects.filter(
            compound=compound,
            status__in=ACTIVE_DISCOVERY_STATUSES,
        ).first()
        if existing is not None:
            return enqueue_literature_discovery_for_compound(
                compound,
                reason,
                priority=priority,
                source_ref=source_ref,
                triggered_by=triggered_by,
            )
        raise
    return target, True


def candidate_compounds_for_literature(
    *,
    limit: int,
    exclude_compound_ids: set[int] | None = None,
    exclude_canonical_inci: tuple[str, ...] = DEFAULT_EXCLUDED_CANONICAL_INCI,
):
    """Backfill: compounds that still need a literature search."""
    if limit <= 0:
        return Compound.objects.none()

    literature_links = CompoundLiterature.objects.filter(compound_id=OuterRef("pk"))
    active_targets = LiteratureDiscoveryTarget.objects.filter(
        compound_id=OuterRef("pk"),
        status__in=ACTIVE_DISCOVERY_STATUSES,
    )
    on_formulation = FormulationIngredient.objects.filter(compound_id=OuterRef("pk"))
    candidates = (
        Compound.objects.annotate(
            has_literature=Exists(literature_links),
            has_active_target=Exists(active_targets),
            on_formulation=Exists(on_formulation),
        )
        .filter(
            Q(
                enrichment_status__in=[
                    EnrichmentStatus.PENDING,
                    EnrichmentStatus.NEEDS_REVIEW,
                ]
            )
            | Q(has_literature=False)
        )
        .filter(has_active_target=False)
        .exclude(canonical_inci__in=exclude_canonical_inci)
        .order_by("-on_formulation", "updated_at", "id")
    )
    if exclude_compound_ids:
        candidates = candidates.exclude(pk__in=exclude_compound_ids)
    return candidates[:limit]


def summarize_compound_result(compound: Compound, name: str, result: Any) -> dict:
    """Stable summary shape for compound discovery results."""
    return {
        "compound_id": compound.pk,
        "name": name,
        "articles_linked": result.articles_linked,
        "related_compounds": result.related_compounds,
        "errors": result.errors,
    }


@dataclass
class LiteratureDiscoveryRunner:
    """Drain compound discovery queue sequentially, then optional backfill."""

    compound_limit: int = 25
    backfill_limit: int = 0
    max_articles: int = 5
    max_related: int = 3
    enrich: bool = False
    max_attempts: int = DEFAULT_MAX_DISCOVERY_ATTEMPTS
    ingest_compound_func: Callable[..., Any] | None = None

    def __post_init__(self) -> None:
        if self.ingest_compound_func is None:
            from literature.ingestion import ingest_compound

            self.ingest_compound_func = ingest_compound

    def run(self) -> dict:
        queue_results: list[dict] = []
        backfill_results: list[dict] = []
        errors: list[str] = []
        processed_compound_ids: set[int] = set()

        targets = list(self._pending_targets()[: self.compound_limit])
        for target in targets:
            try:
                queue_results.append(self.process_target(target))
                processed_compound_ids.add(target.compound_id)
            except Exception as exc:  # noqa: BLE001 - keep the daily crawl moving
                logger.exception(
                    "Literature discovery failed for target %s",
                    target.pk,
                )
                errors.append(f"target:{target.pk}:{exc}")

        remaining = max(0, self.compound_limit - len(queue_results))
        backfill_cap = min(remaining, self.backfill_limit)
        if backfill_cap > 0:
            compounds = candidate_compounds_for_literature(
                limit=backfill_cap,
                exclude_compound_ids=processed_compound_ids,
            )
            for compound in compounds:
                try:
                    backfill_results.append(self.process_compound(compound))
                except Exception as exc:  # noqa: BLE001
                    logger.exception(
                        "Literature discovery backfill failed for compound %s",
                        compound.pk,
                    )
                    errors.append(f"compound:{compound.pk}:{exc}")

        return {
            "targets_processed": len(queue_results),
            "backfill_processed": len(backfill_results),
            "compounds_processed": len(queue_results) + len(backfill_results),
            "targets": queue_results,
            "backfill": backfill_results,
            "errors": errors,
        }

    def _pending_targets(self):
        return LiteratureDiscoveryTarget.objects.filter(
            status=DiscoveryTargetStatus.PENDING,
        ).select_related("compound")

    def process_target(self, target: LiteratureDiscoveryTarget) -> dict:
        claimed = self._claim_target(target)
        if claimed is None:
            compound = target.compound
            return {
                "target_id": target.pk,
                "compound_id": compound.pk,
                "skipped": True,
            }

        target_id, compound, search_name = claimed
        try:
            result = self.ingest_compound_func(
                search_name,
                with_pubmed=True,
                max_articles=self.max_articles,
                max_related=self.max_related,
                enrich=self.enrich,
                asserted_by="literature_discovery_runner",
            )
        except Exception as exc:
            self._record_target_failure(target_id, exc)
            raise

        if result.errors:
            self._record_target_failure(target_id, "; ".join(result.errors))
            summary = summarize_compound_result(compound, search_name, result)
            summary["target_id"] = target_id
            return summary

        self._record_target_success(target_id)
        summary = summarize_compound_result(compound, search_name, result)
        summary["target_id"] = target_id
        return summary

    @transaction.atomic
    def _claim_target(
        self,
        target: LiteratureDiscoveryTarget,
    ) -> tuple[int, Compound, str] | None:
        locked = (
            LiteratureDiscoveryTarget.objects.select_for_update()
            .filter(pk=target.pk, status=DiscoveryTargetStatus.PENDING)
            .select_related("compound")
            .first()
        )
        if locked is None:
            return None

        now = timezone.now()
        locked.status = DiscoveryTargetStatus.RUNNING
        locked.last_run_at = now
        locked.save(update_fields=["status", "last_run_at", "updated_at"])

        compound = locked.compound
        search_name = compound.display_name or compound.canonical_inci
        return locked.pk, compound, search_name

    @transaction.atomic
    def _record_target_failure(
        self,
        target_id: int,
        exc: BaseException | str,
    ) -> None:
        locked = (
            LiteratureDiscoveryTarget.objects.select_for_update()
            .filter(pk=target_id, status=DiscoveryTargetStatus.RUNNING)
            .first()
        )
        if locked is None:
            return

        message = str(exc)
        locked.attempt_count += 1
        locked.last_error = message[:2000]
        if locked.attempt_count >= self.max_attempts:
            locked.status = DiscoveryTargetStatus.SKIPPED
        else:
            locked.status = DiscoveryTargetStatus.PENDING
        locked.save(
            update_fields=[
                "status",
                "attempt_count",
                "last_error",
                "updated_at",
            ]
        )

    @transaction.atomic
    def _record_target_success(self, target_id: int) -> None:
        locked = (
            LiteratureDiscoveryTarget.objects.select_for_update()
            .filter(pk=target_id, status=DiscoveryTargetStatus.RUNNING)
            .first()
        )
        if locked is None:
            return

        locked.status = DiscoveryTargetStatus.COMPLETED
        locked.completed_at = timezone.now()
        locked.last_error = ""
        locked.save(
            update_fields=["status", "completed_at", "last_error", "updated_at"]
        )

    def process_compound(self, compound: Compound) -> dict:
        search_name = compound.display_name or compound.canonical_inci
        result = self.ingest_compound_func(
            search_name,
            with_pubmed=True,
            max_articles=self.max_articles,
            max_related=self.max_related,
            enrich=self.enrich,
            asserted_by="literature_discovery_backfill",
        )
        return summarize_compound_result(compound, search_name, result)


# Backwards-compatible alias for callers/tests migrating to LiteratureDiscoveryRunner.
DailyLiteratureDiscovery = LiteratureDiscoveryRunner
