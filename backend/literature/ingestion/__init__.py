"""External-source ingestion clients and orchestration (PubChem, PubMed, INCI)."""

from . import inci_client
from literature.ingestion.formulation_ingest import (
    FormulationIngestResult,
    create_formulation,
    ingest_formulation,
    ingest_formulation_ingredients,
    parse_inci_list,
)
from literature.ingestion.inci_ingest import InciIngestResult, ingest_inci_ingredient
from literature.ingestion.ingest import IngestResult, ingest_compound

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
