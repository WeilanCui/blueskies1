"""Reusable literature discovery orchestration for scheduled jobs and callers."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable

from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from core.models import (
    Compound,
    EnrichmentStatus,
    Formulation,
    FormulationIngredient,
    Product,
)
from literature.models import (
    ACTIVE_DISCOVERY_STATUSES,
    CompoundLiterature,
    DEFAULT_DISCOVERY_PRIORITY,
    DEFAULT_MAX_DISCOVERY_ATTEMPTS,
    DiscoveryReason,
    DiscoveryTargetStatus,
    LiteratureDiscoveryEvent,
    LiteratureDiscoveryEventStatus,
    LiteratureDiscoveryEventType,
    LiteratureDiscoveryTarget,
    LiteratureDiscoveryTargetType,
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


def _search_label_for_work_item(
    *,
    target_type: str,
    compound: Compound | None = None,
    formulation: Formulation | None = None,
    product: Product | None = None,
) -> str:
    if target_type == LiteratureDiscoveryTargetType.COMPOUND:
        if compound is None:
            return ""
        return compound.display_name or compound.canonical_inci
    if target_type == LiteratureDiscoveryTargetType.FORMULATION:
        return str(formulation) if formulation is not None else ""
    if target_type == LiteratureDiscoveryTargetType.PRODUCT:
        if product is None:
            return ""
        return product.display_name or product.name
    return ""


def _work_item_filter_kwargs(
    *,
    target_type: str,
    compound: Compound | None = None,
    formulation: Formulation | None = None,
    product: Product | None = None,
) -> dict[str, object]:
    if target_type == LiteratureDiscoveryTargetType.COMPOUND:
        if compound is None:
            raise ValueError("compound is required for compound literature discovery")
        return {"compound": compound}
    if target_type == LiteratureDiscoveryTargetType.FORMULATION:
        if formulation is None:
            raise ValueError(
                "formulation is required for formulation literature discovery"
            )
        return {"formulation": formulation}
    if target_type == LiteratureDiscoveryTargetType.PRODUCT:
        if product is None:
            raise ValueError("product is required for product literature discovery")
        return {"product": product}
    raise ValueError(f"Unsupported literature discovery target type: {target_type}")


def _work_item_create_kwargs(
    *,
    target_type: str,
    compound: Compound | None = None,
    formulation: Formulation | None = None,
    product: Product | None = None,
) -> dict[str, object]:
    return {
        "target_type": target_type,
        "compound": (
            compound if target_type == LiteratureDiscoveryTargetType.COMPOUND else None
        ),
        "formulation": (
            formulation if target_type == LiteratureDiscoveryTargetType.FORMULATION else None
        ),
        "product": product if target_type == LiteratureDiscoveryTargetType.PRODUCT else None,
    }


def enqueue_literature_discovery_work_item(
    *,
    target_type: str,
    reason: str,
    compound: Compound | None = None,
    formulation: Formulation | None = None,
    product: Product | None = None,
    priority: int | None = None,
    search_label: str = "",
    source_ref: str = "",
    triggered_by: str = "",
) -> tuple[LiteratureDiscoveryTarget, bool]:
    """Queue one literature discovery work item; idempotent while pending/running."""
    target_type = LiteratureDiscoveryTargetType(target_type)
    filter_kwargs = _work_item_filter_kwargs(
        target_type=target_type,
        compound=compound,
        formulation=formulation,
        product=product,
    )
    create_kwargs = _work_item_create_kwargs(
        target_type=target_type,
        compound=compound,
        formulation=formulation,
        product=product,
    )

    requeue_stale_running_targets(
        compound_id=compound.pk if compound is not None else None,
        formulation_id=formulation.pk if formulation is not None else None,
        product_id=product.pk if product is not None else None,
    )

    if priority is None:
        priority = discovery_priority_for_triggered_by(triggered_by)
    if not search_label:
        search_label = _search_label_for_work_item(
            target_type=target_type,
            compound=compound,
            formulation=formulation,
            product=product,
        )

    existing = LiteratureDiscoveryTarget.objects.filter(
        target_type=target_type,
        status__in=ACTIVE_DISCOVERY_STATUSES,
        **filter_kwargs,
    ).first()
    if existing is not None:
        updates: dict[str, object] = {}
        if reason != existing.reason:
            updates["reason"] = reason
        if priority > existing.priority:
            updates["priority"] = priority
        if search_label and not existing.search_label:
            updates["search_label"] = search_label
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
        with transaction.atomic():
            target = LiteratureDiscoveryTarget.objects.create(
                **create_kwargs,
                reason=reason,
                status=DiscoveryTargetStatus.PENDING,
                priority=priority,
                search_label=search_label,
                source_ref=source_ref,
                triggered_by=triggered_by,
            )
    except IntegrityError:
        existing = LiteratureDiscoveryTarget.objects.filter(
            target_type=target_type,
            status__in=ACTIVE_DISCOVERY_STATUSES,
            **filter_kwargs,
        ).first()
        if existing is not None:
            return enqueue_literature_discovery_work_item(
                target_type=target_type,
                reason=reason,
                compound=compound,
                formulation=formulation,
                product=product,
                priority=priority,
                search_label=search_label,
                source_ref=source_ref,
                triggered_by=triggered_by,
            )
        raise
    return target, True


def enqueue_literature_discovery_for_compound(
    compound: Compound,
    reason: str,
    *,
    priority: int | None = None,
    source_ref: str = "",
    triggered_by: str = "",
) -> tuple[LiteratureDiscoveryTarget, bool]:
    """Queue compound-level literature discovery; idempotent while pending/running."""
    return enqueue_literature_discovery_work_item(
        target_type=LiteratureDiscoveryTargetType.COMPOUND,
        compound=compound,
        reason=reason,
        priority=priority,
        source_ref=source_ref,
        triggered_by=triggered_by,
    )


def _event_type_for_compound(
    *,
    reason: str,
    triggered_by: str,
) -> str:
    if reason == DiscoveryReason.NEW_MIXTURE:
        if triggered_by == "barcode_scan":
            return LiteratureDiscoveryEventType.MIXTURE_CREATED_FROM_PRODUCT
        if triggered_by == "formulation_ingest":
            return LiteratureDiscoveryEventType.MIXTURE_CREATED_FROM_FORMULATION
        return LiteratureDiscoveryEventType.MIXTURE_RESOLVED_FROM_INCI
    if triggered_by == "barcode_scan":
        return LiteratureDiscoveryEventType.COMPOUND_CREATED_FROM_PRODUCT
    if triggered_by == "formulation_ingest":
        return LiteratureDiscoveryEventType.COMPOUND_CREATED_FROM_FORMULATION
    return LiteratureDiscoveryEventType.COMPOUND_RESOLVED_FROM_INCI


def _event_dedupe_key(
    *,
    event_type: str,
    target_type: str,
    target_id: int,
    triggered_by: str = "",
    source_ref: str = "",
) -> str:
    payload = "|".join(
        [event_type, target_type, str(target_id), triggered_by or "", source_ref or ""]
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"literature_discovery:{event_type}:{target_type}:{target_id}:{digest}"


def emit_literature_discovery_event(
    event_type: str,
    *,
    target_type: str = LiteratureDiscoveryTargetType.COMPOUND,
    compound: Compound | None = None,
    formulation: Formulation | None = None,
    product: Product | None = None,
    reason: str = DiscoveryReason.NEW_COMPOUND,
    priority: int | None = None,
    search_label: str = "",
    source_ref: str = "",
    triggered_by: str = "",
    payload: dict | None = None,
    dedupe_key: str | None = None,
    dispatch_on_commit: bool = True,
) -> tuple[LiteratureDiscoveryEvent, bool]:
    """Emit a durable discovery event and schedule dispatch to the work queue."""
    target_type = LiteratureDiscoveryTargetType(target_type)
    filter_kwargs = _work_item_filter_kwargs(
        target_type=target_type,
        compound=compound,
        formulation=formulation,
        product=product,
    )
    target_id = next(iter(filter_kwargs.values())).pk
    if target_id is None:
        raise ValueError("literature discovery events require saved target objects")

    if priority is None:
        priority = discovery_priority_for_triggered_by(triggered_by)
    if not search_label:
        search_label = _search_label_for_work_item(
            target_type=target_type,
            compound=compound,
            formulation=formulation,
            product=product,
        )
    if dedupe_key is None:
        dedupe_key = _event_dedupe_key(
            event_type=event_type,
            target_type=target_type,
            target_id=target_id,
            triggered_by=triggered_by,
            source_ref=source_ref,
        )

    defaults = {
        "event_type": event_type,
        "target_type": target_type,
        "compound": (
            compound if target_type == LiteratureDiscoveryTargetType.COMPOUND else None
        ),
        "formulation": (
            formulation if target_type == LiteratureDiscoveryTargetType.FORMULATION else None
        ),
        "product": product if target_type == LiteratureDiscoveryTargetType.PRODUCT else None,
        "reason": reason,
        "priority": priority,
        "search_label": search_label,
        "source_ref": source_ref,
        "triggered_by": triggered_by,
        "payload": payload or {},
    }

    if dedupe_key:
        event, created = LiteratureDiscoveryEvent.objects.get_or_create(
            dedupe_key=dedupe_key,
            defaults=defaults,
        )
        if not created:
            updates: dict[str, object] = {}
            if priority > event.priority:
                updates["priority"] = priority
            if search_label and not event.search_label:
                updates["search_label"] = search_label
            if source_ref:
                updates["source_ref"] = source_ref
            if triggered_by:
                updates["triggered_by"] = triggered_by
            if event.status in {
                LiteratureDiscoveryEventStatus.FAILED,
                LiteratureDiscoveryEventStatus.SKIPPED,
            }:
                updates["status"] = LiteratureDiscoveryEventStatus.PENDING
                updates["last_error"] = ""
            if updates:
                for field, value in updates.items():
                    setattr(event, field, value)
                event.save(update_fields=[*updates.keys(), "updated_at"])
    else:
        event = LiteratureDiscoveryEvent.objects.create(**defaults)
        created = True

    if event.status == LiteratureDiscoveryEventStatus.PENDING:
        if dispatch_on_commit:
            transaction.on_commit(
                lambda event_id=event.pk: dispatch_literature_discovery_event(event_id)
            )
        else:
            dispatch_literature_discovery_event(event.pk)

    return event, created


def emit_literature_discovery_for_compound(
    compound: Compound,
    reason: str,
    *,
    priority: int | None = None,
    source_ref: str = "",
    triggered_by: str = "",
    payload: dict | None = None,
    dispatch_on_commit: bool = True,
) -> tuple[LiteratureDiscoveryEvent, bool]:
    """Emit a compound-backed literature discovery event."""
    return emit_literature_discovery_event(
        _event_type_for_compound(reason=reason, triggered_by=triggered_by),
        target_type=LiteratureDiscoveryTargetType.COMPOUND,
        compound=compound,
        reason=reason,
        priority=priority,
        source_ref=source_ref,
        triggered_by=triggered_by,
        payload=payload,
        dispatch_on_commit=dispatch_on_commit,
    )


def dispatch_literature_discovery_event(event_id: int) -> dict:
    """Convert one pending outbox event into an idempotent work item."""
    with transaction.atomic():
        event = LiteratureDiscoveryEvent.objects.select_for_update().get(pk=event_id)
        if event.status == LiteratureDiscoveryEventStatus.PROCESSED:
            return {
                "event_id": event.pk,
                "skipped": True,
                "reason": "already_processed",
            }

        try:
            target, created = enqueue_literature_discovery_work_item(
                target_type=event.target_type,
                compound=event.compound,
                formulation=event.formulation,
                product=event.product,
                reason=event.reason,
                priority=event.priority,
                search_label=event.search_label,
                source_ref=event.source_ref,
                triggered_by=event.triggered_by,
            )
        except Exception as exc:  # noqa: BLE001 - preserve event state for retry
            event.attempt_count += 1
            event.status = LiteratureDiscoveryEventStatus.FAILED
            event.last_error = str(exc)[:2000]
            event.save(
                update_fields=[
                    "status",
                    "attempt_count",
                    "last_error",
                    "updated_at",
                ]
            )
            return {
                "event_id": event.pk,
                "created": False,
                "error": event.last_error,
            }

        event.status = LiteratureDiscoveryEventStatus.PROCESSED
        event.processed_at = timezone.now()
        event.last_error = ""
        event.save(
            update_fields=[
                "status",
                "processed_at",
                "last_error",
                "updated_at",
            ]
        )
        return {
            "event_id": event.pk,
            "target_id": target.pk,
            "target_type": target.target_type,
            "created": created,
        }


def dispatch_pending_literature_discovery_events(limit: int = 100) -> dict:
    """Dispatch pending outbox events into the literature discovery work queue."""
    if limit <= 0:
        return {
            "events_processed": 0,
            "events_failed": 0,
            "targets_created": 0,
            "events": [],
        }

    event_ids = list(
        LiteratureDiscoveryEvent.objects.filter(
            status=LiteratureDiscoveryEventStatus.PENDING,
        )
        .order_by("created_at", "id")
        .values_list("id", flat=True)[:limit]
    )
    results: list[dict] = []
    failed = 0
    created = 0
    for event_id in event_ids:
        result = dispatch_literature_discovery_event(event_id)
        results.append(result)
        if result.get("error"):
            failed += 1
        if result.get("created"):
            created += 1

    return {
        "events_processed": len(results),
        "events_failed": failed,
        "targets_created": created,
        "events": results,
    }


DEFAULT_STALE_RUNNING_SECONDS = 3600


def product_discovery_target_filter() -> Q:
    """Targets tied to scanned/formulated products, not literature co-mention stubs."""
    on_formulation = FormulationIngredient.objects.filter(
        compound_id=OuterRef("compound_id"),
    )
    return (
        Q(triggered_by__in=PRODUCT_DISCOVERY_TRIGGERED_BY)
        | Q(Exists(on_formulation))
        | Q(
            target_type__in=[
                LiteratureDiscoveryTargetType.FORMULATION,
                LiteratureDiscoveryTargetType.PRODUCT,
            ]
        )
    )


def requeue_stale_running_targets(
    *,
    stale_after_seconds: int = DEFAULT_STALE_RUNNING_SECONDS,
    compound_id: int | None = None,
    formulation_id: int | None = None,
    product_id: int | None = None,
) -> int:
    """Recover targets left RUNNING after a crashed worker."""
    cutoff = timezone.now() - timedelta(seconds=stale_after_seconds)
    queryset = LiteratureDiscoveryTarget.objects.filter(
        status=DiscoveryTargetStatus.RUNNING,
    ).filter(Q(last_run_at__lt=cutoff) | Q(last_run_at__isnull=True))
    if compound_id is not None:
        queryset = queryset.filter(
            target_type=LiteratureDiscoveryTargetType.COMPOUND,
            compound_id=compound_id,
        )
    if formulation_id is not None:
        queryset = queryset.filter(
            target_type=LiteratureDiscoveryTargetType.FORMULATION,
            formulation_id=formulation_id,
        )
    if product_id is not None:
        queryset = queryset.filter(
            target_type=LiteratureDiscoveryTargetType.PRODUCT,
            product_id=product_id,
        )
    return queryset.update(status=DiscoveryTargetStatus.PENDING)


def candidate_compounds_for_literature(
    *,
    limit: int,
    exclude_compound_ids: set[int] | None = None,
    exclude_canonical_inci: tuple[str, ...] = DEFAULT_EXCLUDED_CANONICAL_INCI,
    formulation_only: bool = False,
):
    """Backfill: compounds that still need a literature search."""
    if limit <= 0:
        return Compound.objects.none()

    literature_links = CompoundLiterature.objects.filter(compound_id=OuterRef("pk"))
    active_targets = LiteratureDiscoveryTarget.objects.filter(
        compound_id=OuterRef("pk"),
        target_type=LiteratureDiscoveryTargetType.COMPOUND,
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
    if formulation_only:
        candidates = candidates.filter(on_formulation=True)
    if exclude_compound_ids:
        candidates = candidates.exclude(pk__in=exclude_compound_ids)
    return candidates[:limit]


def enqueue_pending_compounds_for_literature(
    limit: int,
    *,
    formulation_only: bool = True,
) -> int:
    """Add pending compounds to the discovery queue (formulation ingredients first)."""
    enqueued = 0
    for compound in candidate_compounds_for_literature(
        limit=limit,
        formulation_only=formulation_only,
    ):
        _, created = enqueue_literature_discovery_for_compound(
            compound,
            DiscoveryReason.NEW_COMPOUND,
            priority=PRODUCT_FORMULATION_DISCOVERY_PRIORITY,
            triggered_by="formulation_ingest",
            source_ref=f"enqueue_pending:{compound.pk}",
        )
        if created:
            enqueued += 1
    return enqueued


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
    """Drain literature discovery work items sequentially, then optional backfill."""

    compound_limit: int = 25
    backfill_limit: int | None = None
    max_articles: int = 5
    max_related: int = 3
    enrich: bool = False
    max_attempts: int = DEFAULT_MAX_DISCOVERY_ATTEMPTS
    product_targets_only: bool = True
    backfill_formulation_only: bool = True
    stale_running_seconds: int = DEFAULT_STALE_RUNNING_SECONDS
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

        requeued = requeue_stale_running_targets(
            stale_after_seconds=self.stale_running_seconds,
        )
        if requeued:
            logger.info("Requeued %s stale literature discovery targets", requeued)

        targets = list(self._pending_targets()[: self.compound_limit])
        if not targets and self.product_targets_only:
            logger.info(
                "No pending product/formulation literature discovery targets; "
                "skipping ingest_compound-only queue items"
            )
        for target in targets:
            try:
                target_result = self.process_target(target)
                queue_results.append(target_result)
                if target.compound_id is not None:
                    processed_compound_ids.add(target.compound_id)
            except Exception as exc:  # noqa: BLE001 - keep the daily crawl moving
                logger.exception(
                    "Literature discovery failed for target %s",
                    target.pk,
                )
                errors.append(f"target:{target.pk}:{exc}")

        remaining = max(0, self.compound_limit - len(queue_results))
        if self.backfill_limit is None:
            backfill_cap = remaining
        else:
            backfill_cap = min(remaining, self.backfill_limit)
        if backfill_cap > 0:
            compounds = candidate_compounds_for_literature(
                limit=backfill_cap,
                exclude_compound_ids=processed_compound_ids,
                formulation_only=self.backfill_formulation_only,
            )
            for compound in compounds:
                try:
                    priority = (
                        PRODUCT_FORMULATION_DISCOVERY_PRIORITY
                        if self.backfill_formulation_only
                        else DEFAULT_DISCOVERY_PRIORITY
                    )
                    triggered_by = (
                        "formulation_ingest"
                        if self.backfill_formulation_only
                        else "literature_backfill"
                    )
                    target, _ = enqueue_literature_discovery_for_compound(
                        compound,
                        DiscoveryReason.NEW_COMPOUND,
                        priority=priority,
                        triggered_by=triggered_by,
                        source_ref=f"literature_backfill:{compound.pk}",
                    )
                    backfill_result = self.process_target(target)
                    if not backfill_result.get("skipped"):
                        backfill_results.append(backfill_result)
                except Exception as exc:  # noqa: BLE001
                    logger.exception(
                        "Literature discovery backfill failed for compound %s",
                        compound.pk,
                    )
                    errors.append(f"compound:{compound.pk}:{exc}")

        queue_compounds_processed = sum(
            1
            for result in queue_results
            if result.get("compound_id") is not None and not result.get("skipped")
        )

        return {
            "targets_processed": len(queue_results),
            "backfill_processed": len(backfill_results),
            "compounds_processed": queue_compounds_processed + len(backfill_results),
            "stale_targets_requeued": requeued,
            "targets": queue_results,
            "backfill": backfill_results,
            "errors": errors,
        }

    def _pending_targets(self):
        on_formulation = FormulationIngredient.objects.filter(
            compound_id=OuterRef("compound_id"),
        )
        queryset = (
            LiteratureDiscoveryTarget.objects.filter(
                status=DiscoveryTargetStatus.PENDING,
            )
            .annotate(on_formulation=Exists(on_formulation))
            .select_related("compound", "formulation__product__brand", "product__brand")
        )
        if self.product_targets_only:
            queryset = queryset.filter(product_discovery_target_filter())
        return queryset.order_by(
            "-priority",
            "-on_formulation",
            "created_at",
            "id",
        )

    def process_target(self, target: LiteratureDiscoveryTarget) -> dict:
        locked = self._claim_target(target)
        if locked is None:
            return {
                "target_id": target.pk,
                "target_type": target.target_type,
                "compound_id": target.compound_id,
                "skipped": True,
            }

        target_id = locked.pk
        if locked.target_type != LiteratureDiscoveryTargetType.COMPOUND:
            message = (
                "No literature discovery processor is registered for "
                f"{locked.target_type} targets yet."
            )
            self._record_target_skipped(target_id, message)
            return {
                "target_id": target_id,
                "target_type": locked.target_type,
                "target_object_id": locked.target_id,
                "search_label": locked.search_label,
                "skipped": True,
                "errors": [message],
            }

        compound = locked.compound
        if compound is None:
            message = "Compound literature discovery target is missing its compound."
            self._record_target_skipped(target_id, message)
            return {
                "target_id": target_id,
                "target_type": locked.target_type,
                "compound_id": None,
                "skipped": True,
                "errors": [message],
            }

        search_name = locked.search_label or compound.display_name or compound.canonical_inci
        try:
            assert self.ingest_compound_func is not None
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
    ) -> LiteratureDiscoveryTarget | None:
        locked = (
            LiteratureDiscoveryTarget.objects.select_for_update()
            .filter(pk=target.pk, status=DiscoveryTargetStatus.PENDING)
            .first()
        )
        if locked is None:
            return None

        now = timezone.now()
        locked.status = DiscoveryTargetStatus.RUNNING
        locked.last_run_at = now
        locked.save(update_fields=["status", "last_run_at", "updated_at"])
        # If the worker dies after this commit, requeue_stale_running_targets()
        # resets stale RUNNING rows back to PENDING on the next runner/enqueue pass.

        return locked

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

    @transaction.atomic
    def _record_target_skipped(self, target_id: int, message: str) -> None:
        locked = (
            LiteratureDiscoveryTarget.objects.select_for_update()
            .filter(pk=target_id, status=DiscoveryTargetStatus.RUNNING)
            .first()
        )
        if locked is None:
            return

        locked.status = DiscoveryTargetStatus.SKIPPED
        locked.last_error = message[:2000]
        locked.save(update_fields=["status", "last_error", "updated_at"])

    def process_compound(self, compound: Compound) -> dict:
        search_name = compound.display_name or compound.canonical_inci
        assert self.ingest_compound_func is not None
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
