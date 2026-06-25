"""Orchestrates LLM enrichment over stored literature abstracts."""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from literature.enrichment.extractors import (
    ExtractionContext,
    LiteratureExtraction,
    LiteratureExtractor,
    get_extractor,
)
from core.models import (
    Compound,
    PropertyAssertion,
    PropertyDefinition,
    SourceType,
)
from literature.models import (
    CompoundLiterature,
    LiteratureEnrichmentStatus,
)

logger = logging.getLogger(__name__)


def enrich_literature_link(
    link: CompoundLiterature,
    *,
    extractor: LiteratureExtractor | None = None,
) -> LiteratureExtraction | None:
    """Run extractor on one compound-literature link and persist results."""
    extractor = extractor or get_extractor()
    reference = link.literature
    compound = link.compound
    context = ExtractionContext(
        inci_name=compound.canonical_inci,
        title=reference.title,
        abstract=reference.abstract,
        mesh_terms=list(reference.mesh_terms or []),
    )

    try:
        extraction = extractor.extract(context)
    except Exception as exc:  # noqa: BLE001 - graceful degradation
        logger.exception(
            "Literature enrichment failed for %s / PMID %s",
            compound.canonical_inci,
            reference.pmid,
        )
        link.enrichment_status = LiteratureEnrichmentStatus.FAILED
        link.enriched_by = extractor.name
        link.enriched_at = timezone.now()
        link.save(update_fields=["enrichment_status", "enriched_by", "enriched_at"])
        return None

    with transaction.atomic():
        link.relevance_category = extraction.relevance_category
        link.role_in_paper = extraction.role_in_paper
        link.confidence = extraction.confidence
        link.evidence_summary = extraction.evidence_summary or link.evidence_summary
        link.enrichment_status = LiteratureEnrichmentStatus.ENRICHED
        link.enriched_by = extractor.name
        link.enriched_at = timezone.now()
        link.asserted_by = f"enrichment.{extractor.name}"
        link.save(
            update_fields=[
                "relevance_category",
                "role_in_paper",
                "confidence",
                "evidence_summary",
                "enrichment_status",
                "enriched_by",
                "enriched_at",
                "asserted_by",
            ]
        )
        _merge_literature_functional_classes(
            compound,
            extraction.functional_classes,
            pmid=reference.pmid,
            confidence=extraction.confidence,
            evidence_summary=extraction.evidence_summary,
            extractor_name=extractor.name,
        )

    return extraction


def enrich_compound_literature(
    compound_or_name: Compound | str,
    *,
    reenrich: bool = False,
    extractor: LiteratureExtractor | None = None,
    limit: int | None = None,
    pmid: str | None = None,
) -> list[LiteratureExtraction | None]:
    """Enrich pending (or all, with reenrich) literature links for a compound."""
    if isinstance(compound_or_name, str):
        compound = Compound.objects.get(canonical_inci=compound_or_name.upper())
    else:
        compound = compound_or_name

    links = CompoundLiterature.objects.filter(compound=compound).select_related(
        "literature"
    )
    if pmid:
        links = links.filter(literature__pmid=pmid)
    if not reenrich:
        links = links.filter(enrichment_status=LiteratureEnrichmentStatus.PENDING)
    if limit is not None:
        links = links[:limit]

    results: list[LiteratureExtraction | None] = []
    for link in links:
        results.append(enrich_literature_link(link, extractor=extractor))
    return results


def _merge_literature_functional_classes(
    compound: Compound,
    functional_classes: list[str],
    *,
    pmid: str,
    confidence: float,
    evidence_summary: str,
    extractor_name: str,
) -> None:
    """Write literature-sourced functional_class assertions without clobbering SEED/HUMAN."""
    if not functional_classes:
        return

    try:
        prop = PropertyDefinition.objects.get(key="functional_class")
    except PropertyDefinition.DoesNotExist:
        logger.warning("Missing PropertyDefinition functional_class; run seed_ontology.")
        return

    source_ref = f"pubmed:{pmid}"
    active = PropertyAssertion.objects.filter(
        compound=compound,
        property_def=prop,
        is_active=True,
    ).first()

    existing_lit = PropertyAssertion.objects.filter(
        compound=compound,
        property_def=prop,
        source_ref=source_ref,
    ).first()
    merged = sorted(set(functional_classes))
    if existing_lit and existing_lit.value_json:
        merged = sorted(set(existing_lit.value_json + merged))

    defaults = {
        "value_json": merged,
        "confidence": confidence,
        "source_type": SourceType.LITERATURE,
        "evidence_summary": evidence_summary,
        "asserted_by": f"enrichment.{extractor_name}",
        "source_name": "PubMed",
        "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
    }

    if active and active.source_type in (SourceType.SEED, SourceType.HUMAN):
        assertion, _ = PropertyAssertion.objects.update_or_create(
            compound=compound,
            property_def=prop,
            source_ref=source_ref,
            defaults={**defaults, "is_active": False, "superseded_by": active},
        )
        if assertion.superseded_by_id != active.pk:  # pyright: ignore[reportAttributeAccessIssue]
            assertion.superseded_by = active
            assertion.is_active = False
            assertion.save(update_fields=["superseded_by", "is_active", "updated_at"])
        return

    assertion, created = PropertyAssertion.objects.update_or_create(
        compound=compound,
        property_def=prop,
        source_ref=source_ref,
        defaults={**defaults, "is_active": True, "superseded_by": None},
    )
    if not created:
        for field, value in defaults.items():
            setattr(assertion, field, value)
        assertion.save(update_fields=[*defaults.keys(), "updated_at"])

    if active and active.pk != assertion.pk:
        if _literature_beats(active.source_type, active.confidence, confidence):
            active.is_active = False
            active.superseded_by = assertion
            active.save(update_fields=["is_active", "superseded_by", "updated_at"])
            assertion.is_active = True
            assertion.superseded_by = None
            assertion.save(update_fields=["is_active", "superseded_by", "updated_at"])
        else:
            assertion.is_active = False
            assertion.superseded_by = active
            assertion.save(update_fields=["is_active", "superseded_by", "updated_at"])


def _literature_beats(
    other_source_type: str, other_confidence: float, literature_confidence: float
) -> bool:
    from literature.enrichment.provenance import SOURCE_PRECEDENCE

    lit_rank = SOURCE_PRECEDENCE.get(SourceType.LITERATURE, 0)
    other_rank = SOURCE_PRECEDENCE.get(other_source_type, 0)
    if lit_rank != other_rank:
        return lit_rank > other_rank
    return literature_confidence >= other_confidence
