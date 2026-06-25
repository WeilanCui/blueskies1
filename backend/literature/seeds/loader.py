from django.db import transaction

from core.models import (
    ChemicalClass,
    ChemicalClassMembership,
    Compound,
    CompoundAlias,
    GlossaryTerm,
    PropertyAssertion,
    PropertyDefinition,
    SourceType,
)
from literature.models import InteractionRule
from literature.seeds.chemical_classes import CHEMICAL_CLASSES
from literature.seeds.glossary_terms import GLOSSARY_TERMS
from literature.seeds.interaction_rules import INTERACTION_RULES
from literature.seeds.property_definitions import PROPERTY_DEFINITIONS
from literature.enrichment.compound_bootstrap import apply_entity_classification
from literature.seeds.reference_compounds import REFERENCE_COMPOUNDS


def upsert_property_definitions() -> dict[str, int]:
    created = updated = 0
    for row in PROPERTY_DEFINITIONS:
        defaults = {
            "domain": row["domain"],
            "value_type": row["value_type"],
            "allowed_values": row.get("allowed_values"),
            "label": row["label"],
            "description": row["description"],
            "derivation_hint": row.get("derivation_hint", ""),
            "glossary_categories": row.get("glossary_categories", []),
            "is_agent_writable": row.get("is_agent_writable", True),
            "is_required_for_enrichment": row.get(
                "is_required_for_enrichment", False
            ),
            "sort_order": row.get("sort_order", 0),
        }
        _, was_created = PropertyDefinition.objects.update_or_create(
            key=row["key"],
            defaults=defaults,
        )
        if was_created:
            created += 1
        else:
            updated += 1
    return {"created": created, "updated": updated}


def upsert_glossary_terms() -> dict[str, int]:
    created = updated = 0
    for index, row in enumerate(GLOSSARY_TERMS):
        defaults = {
            "category": row["category"],
            "definition": row["definition"],
            "examples": row.get("examples", []),
            "related_property_keys": row.get("related_property_keys", []),
            "sort_order": row.get("sort_order", index),
        }
        _, was_created = GlossaryTerm.objects.update_or_create(
            slug=row["slug"],
            defaults={**defaults, "term": row["term"]},
        )
        if was_created:
            created += 1
        else:
            updated += 1
    return {"created": created, "updated": updated}


def upsert_interaction_rules() -> dict[str, int]:
    created = updated = 0
    for row in INTERACTION_RULES:
        defaults = {
            "label": row["label"],
            "pattern_a": row["pattern_a"],
            "pattern_b": row.get("pattern_b", ""),
            "vehicle_context": row.get("vehicle_context", ""),
            "interaction_type": row["interaction_type"],
            "risk_class": row["risk_class"],
            "severity": row["severity"],
            "mitigation": row.get("mitigation", ""),
            "evidence_summary": row.get("evidence_summary", ""),
            "source_ref": row.get("source_ref", ""),
            "is_active": True,
        }
        _, was_created = InteractionRule.objects.update_or_create(
            key=row["key"],
            defaults=defaults,
        )
        if was_created:
            created += 1
        else:
            updated += 1
    return {"created": created, "updated": updated}


def _write_assertion(compound: Compound, row: dict) -> None:
    prop = PropertyDefinition.objects.get(key=row["property_key"])
    PropertyAssertion.objects.update_or_create(
        compound=compound,
        property_def=prop,
        is_active=True,
        defaults={
            "value_text": row.get("value_text", ""),
            "value_numeric": row.get("value_numeric"),
            "value_bool": row.get("value_bool"),
            "value_json": row.get("value_json"),
            "confidence": row.get("confidence", 1.0),
            "source_type": row.get("source_type", SourceType.SEED),
            "source_ref": row.get("source_ref", "reference_compounds"),
            "evidence_summary": row.get("evidence_summary", ""),
            "asserted_by": "seed_ontology",
        },
    )


def _write_class_assertion(chemical_class: ChemicalClass, row: dict) -> None:
    prop = PropertyDefinition.objects.get(key=row["property_key"])
    PropertyAssertion.objects.update_or_create(
        chemical_class=chemical_class,
        property_def=prop,
        is_active=True,
        defaults={
            "value_text": row.get("value_text", ""),
            "value_numeric": row.get("value_numeric"),
            "value_bool": row.get("value_bool"),
            "value_json": row.get("value_json"),
            "confidence": row.get("confidence", 1.0),
            "source_type": row.get("source_type", SourceType.SEED),
            "source_ref": row.get("source_ref", "chemical_classes"),
            "evidence_summary": row.get("evidence_summary", ""),
            "asserted_by": "seed_ontology",
        },
    )


@transaction.atomic
def upsert_reference_compounds() -> dict[str, int]:
    compounds_created = assertions_written = 0
    for row in REFERENCE_COMPOUNDS:
        compound, was_created = Compound.objects.update_or_create(
            canonical_inci=row["canonical_inci"],
            defaults={
                "display_name": row.get("display_name", ""),
                "entity_type": row.get("entity_type", "unknown"),
                "primary_cas": row.get("primary_cas", ""),
                "structure_resolvable": row.get("structure_resolvable", False),
                "enrichment_status": "partial",
            },
        )
        if was_created:
            compounds_created += 1

        for alias in row.get("aliases", []):
            CompoundAlias.objects.get_or_create(
                alias_text=alias["alias_text"].upper(),
                alias_type=alias["alias_type"],
                defaults={
                    "compound": compound,
                    "source": "seed",
                },
            )

        for assertion in row.get("assertions", []):
            _write_assertion(compound, assertion)
            assertions_written += 1

        apply_entity_classification(compound, overwrite=False, asserted_by="seed_ontology")

    return {
        "compounds_created": compounds_created,
        "assertions_written": assertions_written,
    }


@transaction.atomic
def upsert_chemical_classes() -> dict[str, int]:
    classes_created = assertions_written = memberships_written = 0
    for row in CHEMICAL_CLASSES:
        parent = None
        if row.get("parent_slug"):
            parent = ChemicalClass.objects.get(slug=row["parent_slug"])
        chemical_class, was_created = ChemicalClass.objects.update_or_create(
            slug=row["slug"],
            defaults={
                "name": row["name"],
                "description": row.get("description", ""),
                "parent": parent,
                "notes": row.get("notes", ""),
            },
        )
        if was_created:
            classes_created += 1

        for assertion in row.get("assertions", []):
            _write_class_assertion(chemical_class, assertion)
            assertions_written += 1

        for member in row.get("members", []):
            compound, _ = Compound.objects.get_or_create(
                canonical_inci=member["canonical_inci"],
                defaults={
                    "display_name": member.get("display_name", ""),
                    "entity_type": member.get("entity_type", "small_molecule"),
                    "structure_resolvable": member.get("structure_resolvable", True),
                    "enrichment_status": "partial",
                },
            )
            ChemicalClassMembership.objects.update_or_create(
                compound=compound,
                chemical_class=chemical_class,
                defaults={
                    "is_primary": member.get("is_primary", False),
                    "is_active": member.get("is_active", True),
                    "rationale": member.get("rationale", ""),
                    "confidence": member.get("confidence", 1.0),
                    "source_type": member.get("source_type", SourceType.SEED),
                    "source_ref": member.get("source_ref", "chemical_classes"),
                    "asserted_by": "seed_ontology",
                },
            )
            memberships_written += 1

    return {
        "classes_created": classes_created,
        "assertions_written": assertions_written,
        "memberships_written": memberships_written,
    }


def seed_all(*, include_reference_compounds: bool = True) -> dict:
    results = {
        "property_definitions": upsert_property_definitions(),
        "glossary_terms": upsert_glossary_terms(),
        "interaction_rules": upsert_interaction_rules(),
    }
    if include_reference_compounds:
        results["reference_compounds"] = upsert_reference_compounds()
        results["chemical_classes"] = upsert_chemical_classes()
    return results
