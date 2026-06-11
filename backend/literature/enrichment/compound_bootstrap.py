from literature.enrichment.entity_classifier import EntityClassification, classify_inci
from core.models import Compound, PropertyAssertion, PropertyDefinition, SourceType


def apply_entity_classification(
    compound: Compound,
    classification: EntityClassification | None = None,
    *,
    overwrite: bool = False,
    asserted_by: str = "entity_classifier",
) -> EntityClassification:
    """Persist classifier output on Compound and as property assertions."""
    result = classification or classify_inci(compound.canonical_inci)

    if overwrite or compound.entity_type == "unknown":
        compound.entity_type = result.entity_type
        compound.structure_resolvable = result.structure_resolvable
        if not compound.notes:
            compound.notes = result.reason
        compound.save(
            update_fields=[
                "entity_type",
                "structure_resolvable",
                "notes",
                "updated_at",
            ]
        )

    _upsert_entity_type_assertion(compound, result, asserted_by=asserted_by)
    _upsert_structure_resolvable_assertion(compound, result, asserted_by=asserted_by)

    for functional_class in result.suggested_functional_classes:
        _upsert_functional_class_hint(
            compound,
            functional_class,
            result,
            asserted_by=asserted_by,
        )

    return result


def _upsert_entity_type_assertion(
    compound: Compound,
    result: EntityClassification,
    *,
    asserted_by: str,
) -> None:
    prop = PropertyDefinition.objects.get(key="entity_type")
    PropertyAssertion.objects.update_or_create(
        compound=compound,
        property_def=prop,
        is_active=True,
        defaults={
            "value_text": result.entity_type,
            "confidence": result.confidence,
            "source_type": SourceType.COMPUTED,
            "source_ref": "entity_classifier",
            "evidence_summary": result.reason,
            "asserted_by": asserted_by,
        },
    )


def _upsert_structure_resolvable_assertion(
    compound: Compound,
    result: EntityClassification,
    *,
    asserted_by: str,
) -> None:
    prop = PropertyDefinition.objects.get(key="structure_resolvable")
    PropertyAssertion.objects.update_or_create(
        compound=compound,
        property_def=prop,
        is_active=True,
        defaults={
            "value_bool": result.structure_resolvable,
            "confidence": result.confidence,
            "source_type": SourceType.COMPUTED,
            "source_ref": "entity_classifier",
            "evidence_summary": result.reason,
            "asserted_by": asserted_by,
        },
    )


def _upsert_functional_class_hint(
    compound: Compound,
    functional_class: str,
    result: EntityClassification,
    *,
    asserted_by: str,
) -> None:
    prop = PropertyDefinition.objects.get(key="functional_class")
    existing = PropertyAssertion.objects.filter(
        compound=compound,
        property_def=prop,
        is_active=True,
    ).first()
    if existing and existing.source_type not in (SourceType.SEED, SourceType.HUMAN):
        return

    merged = [functional_class]
    if existing and existing.value_json:
        merged = sorted(set(existing.value_json + merged))

    PropertyAssertion.objects.update_or_create(
        compound=compound,
        property_def=prop,
        is_active=True,
        defaults={
            "value_json": merged,
            "confidence": min(result.confidence, 0.75),
            "source_type": SourceType.COMPUTED,
            "source_ref": "entity_classifier",
            "evidence_summary": f"Suggested from entity type {result.entity_type}.",
            "asserted_by": asserted_by,
        },
    )
