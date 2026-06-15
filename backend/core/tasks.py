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


def _load_or_create_formulation(
    formulation_id: int | None,
    *,
    product_name: str = "",
    raw_inci_text: str = "",
    brand: str = "",
):
    from literature.ingestion.formulation_ingest import create_formulation
    from core.models import Formulation

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

    formulation = create_formulation(product_name, raw_inci_text, brand=brand)
    return formulation, True


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
            ingest_inci_ingredient(fi.raw_text, asserted_by="barcode_scan")
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
