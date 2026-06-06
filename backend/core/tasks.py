from celery import shared_task


@shared_task
def debug_task() -> str:
    return "Celery is connected."


@shared_task
def ingest_compound_task(name: str, **options) -> dict:
    """Async wrapper around the PubChem + PubMed ingestion orchestrator."""
    from core.ingestion import ingest_compound

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
def ingest_formulation_task(formulation_id: int, **options) -> dict:
    """Async wrapper around formulation ingredient enrichment."""
    from core.ingestion import ingest_formulation_ingredients

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
