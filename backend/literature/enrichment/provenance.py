"""Conflict-resolving property assertion writer with source precedence."""

from __future__ import annotations

import logging

from core.models import Compound, PropertyAssertion, PropertyDefinition, SourceType

logger = logging.getLogger(__name__)

# Idempotent dedup key: (compound, property_def, source_ref).

SOURCE_PRECEDENCE: dict[str, int] = {
    SourceType.HUMAN: 7,
    SourceType.REGULATORY: 6,
    SourceType.LITERATURE: 5,
    SourceType.AGGREGATOR: 4,
    SourceType.COMPUTED: 3,
    SourceType.AGENT: 2,
    SourceType.SEED: 1,
}


def _rank(source_type: str, confidence: float) -> tuple[int, float]:
    return (SOURCE_PRECEDENCE.get(source_type, 0), confidence)


def assert_property(
    compound: Compound,
    key: str,
    *,
    value_text: str = "",
    value_numeric: float | None = None,
    value_bool: bool | None = None,
    value_json: list | dict | None = None,
    source_type: str,
    confidence: float,
    source_ref: str,
    evidence_summary: str = "",
    asserted_by: str = "",
) -> PropertyAssertion | None:
    """Write or update a property assertion with precedence-based conflict resolution."""
    try:
        prop = PropertyDefinition.objects.get(key=key)
    except PropertyDefinition.DoesNotExist:
        logger.warning("Missing PropertyDefinition %r; run seed_ontology.", key)
        return None

    lookup = {
        "compound": compound,
        "property_def": prop,
        "source_ref": source_ref,
    }
    defaults = {
        "value_text": value_text,
        "value_numeric": value_numeric,
        "value_bool": value_bool,
        "value_json": value_json,
        "confidence": confidence,
        "source_type": source_type,
        "evidence_summary": evidence_summary,
        "asserted_by": asserted_by,
    }
    assertion, created = PropertyAssertion.objects.get_or_create(
        **lookup,
        defaults={**defaults, "is_active": True},
    )
    if not created:
        for field, val in defaults.items():
            setattr(assertion, field, val)
        assertion.save(update_fields=[*defaults.keys(), "updated_at"])

    active = (
        PropertyAssertion.objects.filter(
            compound=compound,
            property_def=prop,
            is_active=True,
        )
        .exclude(pk=assertion.pk)
        .first()
    )

    if active is None:
        assertion.is_active = True
        assertion.superseded_by = None
        assertion.save(update_fields=["is_active", "superseded_by", "updated_at"])
        return assertion

    if _rank(assertion.source_type, assertion.confidence) >= _rank(
        active.source_type, active.confidence
    ):
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

    return assertion
