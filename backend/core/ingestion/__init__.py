"""External-source ingestion clients and orchestration (PubChem, PubMed, INCI)."""

from core.ingestion import inci_client
from core.ingestion.formulation_ingest import (
    FormulationIngestResult,
    create_formulation,
    ingest_formulation,
    ingest_formulation_ingredients,
    parse_inci_list,
)
from core.ingestion.inci_ingest import InciIngestResult, ingest_inci_ingredient
from core.ingestion.ingest import IngestResult, ingest_compound

__all__ = [
    "FormulationIngestResult",
    "IngestResult",
    "InciIngestResult",
    "create_formulation",
    "inci_client",
    "ingest_compound",
    "ingest_formulation",
    "ingest_formulation_ingredients",
    "ingest_inci_ingredient",
    "parse_inci_list",
]
