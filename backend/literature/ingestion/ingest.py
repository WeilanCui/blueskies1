"""Orchestrates PubChem + PubMed ingestion for a single compound name."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from django.utils import timezone

from literature.enrichment.compound_bootstrap import apply_entity_classification
from literature.ingestion import pubchem_client, pubmed_client
from literature.ingestion.pubchem_client import PubChemRecord
from literature.ingestion.relevance import (
    build_ux_query,
    classify_relevance,
    infer_role_in_paper,
)
from core.models import (
    Compound,
    CompoundIdentifier,
    CompoundStructure,
    EnrichmentStatus,
    PropertyAssertion,
    PropertyDefinition,
    SourceType,
)
from literature.models import (
    CompoundLiterature,
    CompoundRelationship,
    LiteratureReference,
    RelationshipType,
)

logger = logging.getLogger(__name__)

# PubChem record attr -> computed PropertyDefinition.key
_DESCRIPTOR_MAP = {
    "xlogp": "logP",
    "tpsa": "tpsa",
    "molecular_weight": "molecular_weight",
    "hbd": "hbd",
    "hba": "hba",
}

# Umbrella MeSH substances that should not become compound nodes.
_GENERIC_SUBSTANCE_STOPLIST = {"COSMETICS", "WATER"}


@dataclass
class IngestResult:
    name: str
    compound_id: int | None = None
    cid: int | None = None
    descriptors_written: int = 0
    articles_linked: int = 0
    related_compounds: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"{self.name}: CID={self.cid} descriptors={self.descriptors_written} "
            f"articles={self.articles_linked} related={len(self.related_compounds)} "
            f"errors={len(self.errors)}"
        )


def ingest_compound(
    name: str,
    *,
    max_degree: int = 1,
    max_articles: int = 10,
    max_related: int = 5,
    with_pubmed: bool = True,
    create_related_compounds: bool = False,
    enrich: bool = False,
    extractor: str | None = None,
    asserted_by: str = "ingest_compound",
) -> IngestResult:
    """Resolve a compound from PubChem and pull UX-relevant PubMed literature."""
    result = IngestResult(name=name)

    compound = _get_or_create_compound(name)
    result.compound_id = compound.pk

    record = _safe_pubchem(name, result)
    if record is not None:
        result.cid = record.cid
        _store_pubchem(compound, record, result, asserted_by=asserted_by)

    if with_pubmed:
        _ingest_literature(
            compound,
            name,
            result,
            max_degree=max_degree,
            max_articles=max_articles,
            max_related=max_related,
            create_related_compounds=create_related_compounds,
            asserted_by=asserted_by,
        )

    if enrich and with_pubmed:
        from literature.enrichment import enrich_compound_literature, get_extractor

        enrich_compound_literature(
            compound,
            extractor=get_extractor(extractor),
        )

    _finalize_status(compound)
    return result


def _get_or_create_compound(name: str) -> Compound:
    canonical = " ".join(name.upper().split())
    compound, created = Compound.objects.get_or_create(
        canonical_inci=canonical,
        defaults={"display_name": name.strip()},
    )
    apply_entity_classification(
        compound,
        asserted_by="ingest_compound",
    )
    return compound


def _safe_pubchem(name: str, result: IngestResult) -> PubChemRecord | None:
    try:
        return pubchem_client.fetch_compound(name)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        logger.exception("PubChem ingestion failed for %r", name)
        result.errors.append(f"pubchem:{exc}")
        return None


def _store_pubchem(
    compound: Compound,
    record: PubChemRecord,
    result: IngestResult,
    *,
    asserted_by: str,
) -> None:
    if record.cid is not None:
        _upsert_identifier(compound, "pubchem_cid", str(record.cid), is_primary=True)

    for cas in record.cas_numbers:
        _upsert_identifier(compound, "cas", cas)
    if record.cas_numbers and not compound.primary_cas:
        compound.primary_cas = record.cas_numbers[0]
        compound.save(update_fields=["primary_cas", "updated_at"])

    if record.best_smiles or record.inchi:
        CompoundStructure.objects.update_or_create(
            compound=compound,
            defaults={
                "smiles": record.best_smiles,
                "inchi": record.inchi,
                "inchikey": record.inchikey,
                "molecular_formula": record.molecular_formula,
                "molecular_weight": record.molecular_weight,
                "source": "pubchem",
                "match_quality": "exact",
            },
        )
        if not compound.structure_resolvable:
            compound.structure_resolvable = True
            compound.save(update_fields=["structure_resolvable", "updated_at"])

    source_ref = f"pubchem:CID{record.cid}" if record.cid else "pubchem"
    for attr, key in _DESCRIPTOR_MAP.items():
        value = getattr(record, attr)
        if value is None:
            continue
        if _upsert_computed(compound, key, value, source_ref, asserted_by):
            result.descriptors_written += 1


def _ingest_literature(
    compound: Compound,
    name: str,
    result: IngestResult,
    *,
    max_degree: int,
    max_articles: int,
    max_related: int,
    create_related_compounds: bool,
    asserted_by: str,
) -> None:
    articles = _safe_search(name, max_articles, result)

    for article in articles:
        reference = _upsert_reference(article)
        _link_literature(compound, reference, article, name, degree=0)
        result.articles_linked += 1

    if not create_related_compounds:
        return

    related_names: list[str] = []
    for article in articles:
        related_names.extend(article.substances)

    # Build degree-1 co-mention relationships from substances.
    seen: set[str] = set()
    for substance in related_names:
        canonical = " ".join(substance.upper().split())
        if (
            not canonical
            or canonical in _GENERIC_SUBSTANCE_STOPLIST
            or canonical == compound.canonical_inci
            or canonical in seen
        ):
            continue
        seen.add(canonical)
        if len(result.related_compounds) >= max_related:
            break
        related = _get_or_create_compound(substance)
        _upsert_relationship(compound, related, articles)
        result.related_compounds.append(canonical)

    if max_degree >= 2:
        for canonical in list(result.related_compounds):
            related = Compound.objects.get(canonical_inci=canonical)
            related_articles = _safe_search(
                related.display_name or canonical,
                max_articles=min(max_articles, 5),
                result=result,
            )
            for article in related_articles:
                reference = _upsert_reference(article)
                _link_literature(
                    related, reference, article, related.display_name or canonical,
                    degree=2,
                )
                result.articles_linked += 1


def _safe_search(name: str, max_articles: int, result: IngestResult):
    try:
        pmids = pubmed_client.esearch(build_ux_query(name), retmax=max_articles)
        return pubmed_client.efetch(pmids)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        logger.exception("PubMed ingestion failed for %r", name)
        result.errors.append(f"pubmed:{exc}")
        return []


def _pubmed_url(pmid: str) -> str:
    return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""


def _pmcid_url(pmc_id: str) -> str:
    if not pmc_id:
        return ""
    return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/"


def _upsert_reference(article: pubmed_client.PubMedArticle) -> LiteratureReference:
    reference, _ = LiteratureReference.objects.update_or_create(
        pmid=article.pmid,
        defaults={
            "title": article.title,
            "abstract": article.abstract,
            "journal": article.journal,
            "year": article.year,
            "doi": article.doi,
            "url": _pubmed_url(article.pmid),
            "pmc_id": article.pmc_id,
            "pmcid_url": _pmcid_url(article.pmc_id),
            "mesh_terms": article.mesh_terms,
            "substances": article.substances,
            "source": "pubmed",
        },
    )
    return reference


def _link_literature(
    compound: Compound,
    reference: LiteratureReference,
    article: pubmed_client.PubMedArticle,
    name: str,
    *,
    degree: int,
) -> None:
    category = classify_relevance(article.mesh_terms, article.title, article.abstract)
    role = infer_role_in_paper(name, article.title, article.abstract)
    confidence = 0.7 if degree == 0 else max(0.3, 0.6 - 0.1 * degree)
    CompoundLiterature.objects.update_or_create(
        compound=compound,
        literature=reference,
        defaults={
            "relevance_category": category,
            "role_in_paper": role,
            "relationship_degree": degree,
            "confidence": confidence,
            "evidence_summary": article.title,
            "source_type": SourceType.LITERATURE,
            "source_name": "PubMed",
            "source_ref": f"pubmed:{article.pmid}",
            "source_url": reference.best_read_url,
            "asserted_by": "ingest.pubmed",
            "retrieved_at": timezone.now(),
        },
    )


def _upsert_relationship(
    compound: Compound,
    related: Compound,
    articles: list[pubmed_client.PubMedArticle],
) -> None:
    pmids = ",".join(a.pmid for a in articles)
    CompoundRelationship.objects.update_or_create(
        compound_a=compound,
        compound_b=related,
        relationship_type=RelationshipType.CO_MENTION,
        defaults={
            "degree": 1,
            "source_type": SourceType.LITERATURE,
            "source_name": "PubMed",
            "source_ref": f"pubmed:{pmids}" if pmids else "",
            "source_url": (
                _pubmed_url(articles[0].pmid) if articles else ""
            ),
            "evidence_summary": f"Co-mentioned with {compound.canonical_inci} in PubMed.",
            "confidence": 0.5,
            "asserted_by": "ingest.pubmed",
            "retrieved_at": timezone.now(),
        },
    )


def _upsert_identifier(
    compound: Compound,
    id_type: str,
    id_value: str,
    *,
    is_primary: bool = False,
) -> None:
    CompoundIdentifier.objects.update_or_create(
        id_type=id_type,
        id_value=id_value,
        defaults={
            "compound": compound,
            "source": "pubchem",
            "is_primary": is_primary,
        },
    )


def _upsert_computed(
    compound: Compound,
    key: str,
    value: float,
    source_ref: str,
    asserted_by: str,
) -> bool:
    try:
        prop = PropertyDefinition.objects.get(key=key)
    except PropertyDefinition.DoesNotExist:
        logger.warning("Missing PropertyDefinition %r; run seed_ontology.", key)
        return False
    PropertyAssertion.objects.update_or_create(
        compound=compound,
        property_def=prop,
        is_active=True,
        defaults={
            "value_numeric": value,
            "confidence": 1.0,
            "source_type": SourceType.COMPUTED,
            "source_ref": source_ref,
            "evidence_summary": "PubChem computed descriptor.",
            "asserted_by": asserted_by,
        },
    )
    return True


def _finalize_status(compound: Compound) -> None:
    has_structure = CompoundStructure.objects.filter(compound=compound).exists()
    has_literature = CompoundLiterature.objects.filter(compound=compound).exists()
    if has_structure or has_literature:
        if compound.enrichment_status == EnrichmentStatus.PENDING:
            compound.enrichment_status = EnrichmentStatus.PARTIAL
            compound.save(update_fields=["enrichment_status", "updated_at"])
