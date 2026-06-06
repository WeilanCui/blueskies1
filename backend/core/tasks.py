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
