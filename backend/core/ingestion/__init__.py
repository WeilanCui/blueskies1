"""External-source ingestion clients and orchestration (PubChem, PubMed, INCI)."""

from core.ingestion import inci_client
from core.ingestion.inci_ingest import InciIngestResult, ingest_inci_ingredient
from core.ingestion.ingest import IngestResult, ingest_compound

__all__ = [
    "IngestResult",
    "InciIngestResult",
    "inci_client",
    "ingest_compound",
    "ingest_inci_ingredient",
]
