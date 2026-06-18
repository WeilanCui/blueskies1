import hashlib
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def debug_task() -> str:
    return "Celery is connected."


@shared_task
def ingest_compound_task(name: str, **options) -> dict:
    """Async wrapper around the PubChem + PubMed ingestion orchestrator."""
    from literature.ingestion import ingest_compound

    result = ingest_compound(name, **options)
    return {
        "name": result.name,
        "compound_id": result.compound_id,
        "cid": result.cid,
        "descriptors_written": result.descriptors_written,
        "articles_linked": result.articles_linked,
        "related_compounds": result.related_compounds,
        "errors": result.errors,
    }


@shared_task
def enrich_literature_task(
    compound_id: int | None = None,
    pmid: str | None = None,
    **options,
) -> dict:
    """Async wrapper around literature LLM enrichment."""
    from literature.enrichment import enrich_compound_literature, get_extractor
    from core.models import Compound

    extractor = get_extractor(options.pop("extractor", None))
    if compound_id is not None:
        compound = Compound.objects.get(pk=compound_id)
        results = enrich_compound_literature(
            compound,
            pmid=pmid,
            extractor=extractor,
            **options,
        )
        return {
            "compound_id": compound_id,
            "enriched": sum(1 for item in results if item is not None),
            "total": len(results),
            "extractor": extractor.name,
        }

    from core.models import CompoundLiterature, LiteratureEnrichmentStatus

    compound_ids = (
        CompoundLiterature.objects.filter(
            enrichment_status=LiteratureEnrichmentStatus.PENDING
        )
        .values_list("compound_id", flat=True)
        .distinct()
    )
    total_enriched = 0
    for cid in compound_ids:
        compound = Compound.objects.get(pk=cid)
        results = enrich_compound_literature(
            compound,
            pmid=pmid,
            extractor=extractor,
            **options,
        )
        total_enriched += sum(1 for item in results if item is not None)
    return {
        "compound_id": None,
        "enriched": total_enriched,
        "extractor": extractor.name,
    }


@shared_task
def daily_literature_discovery_task(
    *,
    compound_limit: int = 25,
    backfill_limit: int | None = -1,
    event_limit: int = 100,
    drain_countdown: int = 60,
    max_articles: int = 5,
    max_related: int = 3,
    enrich: bool = False,
) -> dict:
    """Seed discovery targets and kick off the queue drainer."""
    from literature.discovery import (
        enqueue_pending_compounds_for_literature,
        pending_literature_discovery_target_count,
    )

    seed_limit = (
        compound_limit
        if backfill_limit is None or backfill_limit < 0
        else backfill_limit
    )
    seeded = enqueue_pending_compounds_for_literature(
        seed_limit,
        formulation_only=True,
    )
    pending_before_drain = pending_literature_discovery_target_count()

    drain_literature_discovery_queue.apply_async(
        kwargs={
            "compound_limit": compound_limit,
            "event_limit": event_limit,
            "drain_countdown": drain_countdown,
            "max_articles": max_articles,
            "max_related": max_related,
            "enrich": enrich,
        }
    )

    return {
        "targets_seeded": seeded,
        "pending_targets": pending_before_drain,
        "drain_scheduled": True,
    }


@shared_task
def drain_literature_discovery_queue(
    *,
    compound_limit: int = 25,
    event_limit: int = 100,
    drain_countdown: int = 60,
    max_articles: int = 5,
    max_related: int = 3,
    enrich: bool = False,
    product_targets_only: bool = True,
) -> dict:
    """Drain a bounded batch of literature targets and reschedule while work remains."""
    from literature.discovery import (
        LiteratureDiscoveryRunner,
        dispatch_pending_literature_discovery_events,
        pending_literature_discovery_event_count,
        pending_literature_discovery_target_count,
    )

    event_result = dispatch_pending_literature_discovery_events(limit=event_limit)
    result = LiteratureDiscoveryRunner(
        compound_limit=compound_limit,
        backfill_limit=0,
        max_articles=max_articles,
        max_related=max_related,
        enrich=enrich,
        product_targets_only=product_targets_only,
    ).run()

    pending_remaining = pending_literature_discovery_target_count(
        product_targets_only=product_targets_only,
    )
    pending_events_remaining = pending_literature_discovery_event_count()
    rescheduled = (
        (pending_remaining > 0 and compound_limit > 0)
        or (pending_events_remaining > 0 and event_limit > 0)
    )
    if rescheduled:
        drain_literature_discovery_queue.apply_async(
            kwargs={
                "compound_limit": compound_limit,
                "event_limit": event_limit,
                "drain_countdown": drain_countdown,
                "max_articles": max_articles,
                "max_related": max_related,
                "enrich": enrich,
                "product_targets_only": product_targets_only,
            },
            countdown=drain_countdown,
        )

    result["events"] = event_result
    result["pending_remaining"] = pending_remaining
    result["pending_events_remaining"] = pending_events_remaining
    result["rescheduled"] = rescheduled
    return result


def _load_or_create_formulation(
    formulation_id: int | None,
    *,
    product_name: str = "",
    raw_inci_text: str = "",
    brand: str = "",
):
    from literature.ingestion.formulation_ingest import (
        _get_or_create_product,
        create_formulation,
        parse_inci_list,
    )
    from core.models import Formulation
    from django.db import transaction

    if formulation_id is not None:
        formulation = (
            Formulation.objects.prefetch_related("ingredients")
            .filter(pk=formulation_id)
            .first()
        )
        if formulation is not None:
            return formulation, False

    if not product_name.strip() or not raw_inci_text.strip():
        return None, False

    source_ref = _formulation_task_source_ref(
        product_name,
        raw_inci_text,
        brand=brand,
        ingredient_names=parse_inci_list(raw_inci_text),
    )
    existing = (
        Formulation.objects.prefetch_related("ingredients")
        .filter(source_ref=source_ref)
        .first()
    )
    if existing is not None:
        return existing, False

    with transaction.atomic():
        product = _get_or_create_product(product_name, brand=brand)
        ProductModel = type(product)
        ProductModel.objects.select_for_update().get(pk=product.pk)
        existing = (
            Formulation.objects.prefetch_related("ingredients")
            .filter(source_ref=source_ref)
            .first()
        )
        if existing is not None:
            return existing, False

        formulation = create_formulation(product_name, raw_inci_text, brand=brand)
        formulation.source_ref = source_ref
        formulation.save(update_fields=["source_ref", "updated_at"])
    return formulation, True


def _formulation_task_source_ref(
    product_name: str,
    raw_inci_text: str,
    *,
    brand: str = "",
    ingredient_names: list[str] | None = None,
) -> str:
    ingredients = ingredient_names if ingredient_names is not None else []
    normalized_ingredients = ",".join(
        " ".join(name.upper().split()) for name in ingredients
    )
    if not normalized_ingredients:
        normalized_ingredients = " ".join(raw_inci_text.upper().split())
    payload = "|".join(
        [
            "task_formulation",
            " ".join(brand.upper().split()),
            " ".join((product_name.strip() or "Unnamed product").upper().split()),
            normalized_ingredients,
        ]
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"task:formulation:{digest}"


@shared_task
def enrich_formulation_ingredients(
    formulation_id: int | None = None,
    *,
    product_name: str = "",
    raw_inci_text: str = "",
    brand: str = "",
) -> dict:
    """Best-effort INCI enrichment for every ingredient on a barcode-scanned formulation.

    Iterates FormulationIngredient rows, calls ingest_inci_ingredient for each,
    then sets the formulation's enrichment_status to PARTIAL (some may have enriched)
    or keeps PENDING if nothing succeeded.
    """
    from literature.ingestion.inci_ingest import ingest_inci_ingredient
    from core.models import EnrichmentStatus

    formulation, created = _load_or_create_formulation(
        formulation_id,
        product_name=product_name,
        raw_inci_text=raw_inci_text,
        brand=brand,
    )
    if formulation is None:
        logger.error(
            "enrich_formulation_ingredients: formulation %s not found and no creation payload provided",
            formulation_id,
        )
        return {
            "formulation_id": formulation_id,
            "created": False,
            "error": "not found; product_name and raw_inci_text are required to create",
        }

    success_count = 0
    error_count = 0
    for fi in formulation.ingredients.all():
        try:
            result = ingest_inci_ingredient(fi.raw_text, asserted_by="barcode_scan")
            if result.errors:
                error_count+=1
            else:
                success_count += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "enrich_formulation_ingredients: failed for %r (formulation=%s): %s",
                fi.raw_text,
                formulation_id,
                exc,
            )
            error_count += 1

    # Update formulation enrichment_status based on outcome.
    if success_count > 0:
        new_status = (
            EnrichmentStatus.PARTIAL
            if error_count > 0
            else EnrichmentStatus.PARTIAL  # full per-ingredient enrichment runs separately
        )
    else:
        new_status = EnrichmentStatus.PENDING

    formulation.enrichment_status = new_status
    formulation.save(update_fields=["enrichment_status", "updated_at"])

    return {
        "formulation_id": formulation.pk,
        "created": created,
        "success_count": success_count,
        "error_count": error_count,
        "enrichment_status": new_status,
    }


@shared_task
def ingest_formulation_task(formulation_id: int, **options) -> dict:
    """Async wrapper around formulation ingredient enrichment."""
    from literature.ingestion import ingest_formulation_ingredients

    result = ingest_formulation_ingredients(formulation_id, **options)
    return {
        "formulation_id": result.formulation_id,
        "product_name": result.product_name,
        "ingredient_count": result.ingredient_count,
        "enrichment_status": result.enrichment_status,
        "ingredients": [
            {
                "name": item.name,
                "position": item.position,
                "compound_id": item.compound_id,
                "parse_status": item.parse_status,
                "inci_properties": item.inci_properties,
                "pubchem_descriptors": item.pubchem_descriptors,
                "articles_linked": item.articles_linked,
                "errors": item.errors,
            }
            for item in result.ingredients
        ],
    }
