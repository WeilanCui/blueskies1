from celery import shared_task


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
