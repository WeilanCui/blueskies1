from django.db import transaction

from skinconcerns.models import (
    ConcernAlias,
    ConcernEvidence,
    ConcernReferralTrigger,
    ConcernRule,
    RecommendationPolicy,
    SkinConcern,
)
from skinconcerns.normalization import normalize_search_text
from skinconcerns.seeds.concerns import CONCERNS, REFERRAL_TRIGGERS, SOURCES


def _alias_payload(alias) -> tuple[str, str]:
    if isinstance(alias, tuple):
        return alias
    return alias, "consumer"


def _deactivate_stale(model, field_name: str, active_values: set[str]) -> int:
    return (
        model.objects.filter(is_active=True)
        .exclude(**{f"{field_name}__in": active_values})
        .update(is_active=False)
    )


@transaction.atomic
def seed_skin_concerns() -> dict[str, int]:
    counts = {
        "concerns_created": 0,
        "concerns_updated": 0,
        "aliases_written": 0,
        "rules_written": 0,
        "evidence_written": 0,
        "triggers_written": 0,
        "concerns_deactivated": 0,
        "aliases_deactivated": 0,
        "rules_deactivated": 0,
        "evidence_deactivated": 0,
        "triggers_deactivated": 0,
    }
    concerns_by_slug: dict[str, SkinConcern] = {}
    active_concern_slugs = {row["slug"] for row in CONCERNS}
    active_aliases: set[str] = set()
    active_rule_keys: set[str] = set()
    active_evidence_keys: set[str] = set()
    active_trigger_keys = {trigger[1] for trigger in REFERRAL_TRIGGERS}

    for row in CONCERNS:
        concern, was_created = SkinConcern.objects.update_or_create(
            slug=row["slug"],
            defaults={
                "display_name": row["display_name"],
                "consumer_label": row["consumer_label"],
                "description": row.get("description", ""),
                "group": row["group"],
                "concern_type": row["concern_type"],
                "recommendation_policy": row["recommendation_policy"],
                "copy_mode": row["copy_mode"],
                "is_common": row.get("is_common", True),
                "is_active": row.get("is_active", True),
            },
        )
        concerns_by_slug[concern.slug] = concern
        if was_created:
            counts["concerns_created"] += 1
        else:
            counts["concerns_updated"] += 1

        for alias in row.get("aliases", []):
            alias_text, alias_type = _alias_payload(alias)
            active_aliases.add(normalize_search_text(alias_text))
            ConcernAlias.objects.update_or_create(
                normalized_alias=normalize_search_text(alias_text),
                defaults={
                    "concern": concern,
                    "alias_text": alias_text,
                    "alias_type": alias_type,
                    "is_active": True,
                },
            )
            counts["aliases_written"] += 1

        for rule_row in row.get("rules", []):
            active_rule_keys.add(rule_row["key"])
            ConcernRule.objects.update_or_create(
                key=rule_row["key"],
                defaults={
                    "concern": concern,
                    "label": rule_row["label"],
                    "rule_kind": rule_row["rule_kind"],
                    "target_type": rule_row["target_type"],
                    "product_category": rule_row.get("product_category", ""),
                    "chemical_class": rule_row.get("chemical_class"),
                    "compound": rule_row.get("compound"),
                    "property_def": rule_row.get("property_def"),
                    "raw_target": rule_row.get("raw_target", ""),
                    "weight": rule_row.get("weight", 10),
                    "rationale": rule_row.get("rationale", ""),
                    "is_active": True,
                },
            )
            counts["rules_written"] += 1

        for source_key in row.get("sources", []):
            evidence_key = f"{concern.slug}-{source_key}"
            active_evidence_keys.add(evidence_key)
            source = SOURCES[source_key]
            ConcernEvidence.objects.update_or_create(
                key=evidence_key,
                defaults={
                    "concern": concern,
                    "source_name": source["source_name"],
                    "source_url": source["source_url"],
                    "citation_label": source["citation_label"],
                    "evidence_type": source["evidence_type"],
                    "notes": source.get("notes", ""),
                    "is_active": True,
                },
            )
            counts["evidence_written"] += 1

    for concern_slug, key, trigger_text, severity in REFERRAL_TRIGGERS:
        ConcernReferralTrigger.objects.update_or_create(
            key=key,
            defaults={
                "concern": concerns_by_slug[concern_slug],
                "trigger_text": trigger_text,
                "description": "Suppress routine product recommendations and use clinician-safe guidance.",
                "severity": severity,
                "policy_override": RecommendationPolicy.SUPPRESS,
                "is_active": True,
            },
        )
        counts["triggers_written"] += 1

    counts["concerns_deactivated"] = _deactivate_stale(
        SkinConcern,
        "slug",
        active_concern_slugs,
    )
    counts["aliases_deactivated"] = _deactivate_stale(
        ConcernAlias,
        "normalized_alias",
        active_aliases,
    )
    counts["rules_deactivated"] = _deactivate_stale(
        ConcernRule,
        "key",
        active_rule_keys,
    )
    counts["evidence_deactivated"] = _deactivate_stale(
        ConcernEvidence,
        "key",
        active_evidence_keys,
    )
    counts["triggers_deactivated"] = _deactivate_stale(
        ConcernReferralTrigger,
        "key",
        active_trigger_keys,
    )

    return counts
