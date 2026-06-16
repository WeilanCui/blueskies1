"""Orchestrates INCI API ingredient ingestion into Compound + property assertions."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from literature.enrichment.compound_bootstrap import apply_entity_classification
from literature.enrichment.provenance import assert_property
from literature.ingestion import inci_client
from literature.ingestion.inci_client import InciIngredient
from core.models import Compound, CompoundAlias, CompoundIdentifier, SourceType

logger = logging.getLogger(__name__)

_CONF_SAFETY = 0.5
_CONF_STRUCTURAL = 0.6

_FUNCTION_MAP: dict[str, str] = {
    "ANTIOXIDANT": "antioxidant",
    "SKIN CONDITIONING": "emollient",
    "SKIN CONDITIONING - EMOLLIENT": "emollient",
    "SKIN CONDITIONING - HUMECTANT": "humectant",
    "HUMECTANT": "humectant",
    "SOLVENT": "solvent",
    "PRESERVATIVE": "preservative",
    "EMULSIFYING": "emulsifier",
    "EMULSIFIER": "emulsifier",
    "SURFACTANT": "surfactant",
    "SURFACTANT - CLEANSING": "surfactant",
    "VISCOSITY CONTROLLING": "thickener_rheology_modifier",
    "SKIN PROTECTING": "occlusive",
    "FRAGRANCE": "fragrance",
    "COLORANT": "colorant",
    "CHELATING": "chelator",
    "PH ADJUSTER": "ph_adjuster",
    "SOLUBILIZING": "solubilizer",
}

_EFFICACY_FROM_FUNCTION: dict[str, str] = {
    "BRIGHTENING": "brightening",
    "SKIN BRIGHTENING": "brightening",
    "ANTI-ACNE": "anti_acne",
    "ANTI ACNE": "anti_acne",
    "ANTACNE": "anti_acne",
}

_PREGNANCY_MAP = {
    "safe": "safe",
    "unsafe": "unsafe",
    "caution": "caution",
    "unknown": "unknown",
}

_EU_STATUS_MAP = {
    "allowed": "allowed",
    "restricted": "restricted",
    "prohibited": "prohibited",
    "unknown": "unknown",
}


@dataclass
class PropertyClaim:
    key: str
    value_text: str = ""
    value_numeric: float | None = None
    value_bool: bool | None = None
    value_json: list | dict | None = None
    confidence: float = _CONF_SAFETY
    evidence_summary: str = ""


@dataclass
class InciIngestResult:
    name: str
    compound_id: int | None = None
    aliases_added: int = 0
    identifiers_added: int = 0
    properties_written: int = 0
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"{self.name}: compound_id={self.compound_id} "
            f"aliases={self.aliases_added} identifiers={self.identifiers_added} "
            f"properties={self.properties_written} errors={len(self.errors)}"
        )


def ingest_inci_ingredient(
    name: str,
    *,
    asserted_by: str = "ingest_inci",
) -> InciIngestResult:
    """Fetch an ingredient from the INCI API and persist mapped properties."""
    result = InciIngestResult(name=name)
    compound = _get_or_create_compound(name)
    result.compound_id = compound.pk

    ingredient = _safe_fetch(name, result)
    if ingredient is None:
        return result

    source_ref = f"inciapi:{ingredient.inci_name}"
    result.identifiers_added += _store_identifiers(compound, ingredient)
    result.aliases_added += _store_aliases(compound, ingredient)

    for claim in map_ingredient(ingredient):
        if assert_property(
            compound,
            claim.key,
            value_text=claim.value_text,
            value_numeric=claim.value_numeric,
            value_bool=claim.value_bool,
            value_json=claim.value_json,
            source_type=SourceType.AGGREGATOR,
            confidence=claim.confidence,
            source_ref=source_ref,
            evidence_summary=claim.evidence_summary,
            asserted_by=asserted_by,
        ):
            result.properties_written += 1

    if ingredient.raw:
        if assert_property(
            compound,
            "inci_profile",
            value_json=ingredient.raw,
            source_type=SourceType.AGGREGATOR,
            confidence=_CONF_STRUCTURAL,
            source_ref=source_ref,
            evidence_summary="Full INCI API ingredient response.",
            asserted_by=asserted_by,
        ):
            result.properties_written += 1

    return result


def map_ingredient(ingredient: InciIngredient) -> list[PropertyClaim]:
    """Pure mapping from a typed INCI record to property claims."""
    claims: list[PropertyClaim] = []

    functional_classes = _map_functions(ingredient.functions)
    if functional_classes:
        claims.append(
            PropertyClaim(
                key="functional_class",
                value_json=functional_classes,
                confidence=_CONF_STRUCTURAL,
                evidence_summary="INCI API function tags.",
            )
        )

    efficacy = _map_efficacy(ingredient.functions)
    if efficacy:
        claims.append(
            PropertyClaim(
                key="efficacy_domain",
                value_json=efficacy,
                confidence=_CONF_SAFETY,
                evidence_summary="INCI API function-derived efficacy hints.",
            )
        )

    if ingredient.safety_score is not None:
        claims.append(
            PropertyClaim(
                key="inci_safety_score",
                value_numeric=ingredient.safety_score,
                confidence=_CONF_SAFETY,
                evidence_summary="INCI API algorithmic safety score (1-10).",
            )
        )

    comedogenic = _map_comedogenicity(ingredient.comedogenicity_rating)
    if comedogenic:
        claims.append(
            PropertyClaim(
                key="comedogenic_risk",
                value_text=comedogenic,
                confidence=_CONF_SAFETY,
                evidence_summary="INCI API comedogenicity rating.",
            )
        )

    irritancy = _map_irritancy(ingredient.irritancy_potential)
    if irritancy:
        claims.append(
            PropertyClaim(
                key="irritation_potential",
                value_text=irritancy,
                confidence=_CONF_SAFETY,
                evidence_summary="INCI API irritancy potential.",
            )
        )

    sensitization = _map_sensitization(
        ingredient.is_eu_allergen, ingredient.allergen_types
    )
    if sensitization:
        claims.append(
            PropertyClaim(
                key="sensitization_potential",
                value_text=sensitization,
                confidence=_CONF_SAFETY,
                evidence_summary="INCI API EU allergen status.",
            )
        )

    ph_range = _parse_ph_range(ingredient.optimal_ph_range)
    if ph_range:
        claims.append(
            PropertyClaim(
                key="ph_stability_range",
                value_json=ph_range,
                confidence=_CONF_SAFETY,
                evidence_summary="INCI API optimal pH range.",
            )
        )

    if ingredient.photosensitivity_risk.lower() in ("moderate", "high"):
        claims.append(
            PropertyClaim(
                key="light_sensitive",
                value_bool=True,
                confidence=_CONF_SAFETY,
                evidence_summary="INCI API photosensitivity risk.",
            )
        )

    if ingredient.stability.lower() == "unstable":
        claims.append(
            PropertyClaim(
                key="oxidation_sensitive",
                value_bool=True,
                confidence=_CONF_STRUCTURAL,
                evidence_summary="INCI API stability flag.",
            )
        )

    evidence = _map_evidence_quality(ingredient.evidence_quality)
    if evidence:
        claims.append(
            PropertyClaim(
                key="evidence_strength",
                value_text=evidence,
                confidence=_CONF_SAFETY,
                evidence_summary="INCI API evidence quality score.",
            )
        )

    pregnancy = _PREGNANCY_MAP.get(ingredient.pregnancy_safe.lower())
    if pregnancy:
        claims.append(
            PropertyClaim(
                key="pregnancy_safe",
                value_text=pregnancy,
                confidence=_CONF_SAFETY,
                evidence_summary="INCI API pregnancy safety flag.",
            )
        )

    eu_status = _EU_STATUS_MAP.get(ingredient.eu_status.lower())
    if eu_status:
        claims.append(
            PropertyClaim(
                key="eu_regulatory_status",
                value_text=eu_status,
                confidence=_CONF_SAFETY,
                evidence_summary="INCI API EU regulatory status.",
            )
        )

    if ingredient.suitable_for_skin_types:
        claims.append(
            PropertyClaim(
                key="suitable_skin_types",
                value_json=ingredient.suitable_for_skin_types,
                confidence=_CONF_SAFETY,
                evidence_summary="INCI API suitable skin types.",
            )
        )

    if ingredient.avoid_for_skin_types:
        claims.append(
            PropertyClaim(
                key="avoid_skin_types",
                value_json=ingredient.avoid_for_skin_types,
                confidence=_CONF_SAFETY,
                evidence_summary="INCI API skin types to avoid.",
            )
        )

    return claims


def _get_or_create_compound(name: str) -> Compound:
    canonical = " ".join(name.upper().split())
    compound, created = Compound.objects.get_or_create(
        canonical_inci=canonical,
        defaults={"display_name": name.strip()},
    )
    classification = apply_entity_classification(compound, asserted_by="ingest_inci")
    if created:
        from core.models import EntityType
        from core.models.literature_discovery_target import DiscoveryReason
        from literature.discovery import enqueue_literature_discovery_for_compound

        reason = (
            DiscoveryReason.NEW_MIXTURE
            if classification.entity_type == EntityType.MIXTURE
            else DiscoveryReason.NEW_COMPOUND
        )
        enqueue_literature_discovery_for_compound(
            compound,
            reason,
            triggered_by="ingest_inci",
            source_ref=f"get_or_create_compound:{canonical}",
        )
    return compound


def _safe_fetch(name: str, result: InciIngestResult) -> InciIngredient | None:
    try:
        return inci_client.get_ingredient(name)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        logger.exception("INCI API ingestion failed for %r", name)
        result.errors.append(f"inci:{exc}")
        return None


def _store_identifiers(compound: Compound, ingredient: InciIngredient) -> int:
    added = 0
    if ingredient.cas_number:
        _, created = CompoundIdentifier.objects.update_or_create(
            id_type="cas",
            id_value=ingredient.cas_number,
            defaults={
                "compound": compound,
                "source": "inciapi",
                "is_primary": False,
            },
        )
        if created:
            added += 1
        if not compound.primary_cas:
            compound.primary_cas = ingredient.cas_number
            compound.save(update_fields=["primary_cas", "updated_at"])

    if ingredient.ec_number:
        _, created = CompoundIdentifier.objects.update_or_create(
            id_type="ec",
            id_value=ingredient.ec_number,
            defaults={
                "compound": compound,
                "source": "inciapi",
                "is_primary": False,
            },
        )
        if created:
            added += 1
    return added


def _store_aliases(compound: Compound, ingredient: InciIngredient) -> int:
    added = 0
    for alias in ingredient.aliases:
        text = alias.strip()
        if not text:
            continue
        _, created = CompoundAlias.objects.get_or_create(
            alias_text=text,
            alias_type="inci",
            defaults={"compound": compound, "source": "inciapi"},
        )
        if created:
            added += 1
    return added


def _normalize_function_tag(tag: str) -> str:
    return " ".join(tag.upper().split())


def _map_functions(functions: list[str]) -> list[str]:
    mapped: list[str] = []
    for tag in functions:
        key = _normalize_function_tag(tag)
        value = _FUNCTION_MAP.get(key)
        if value and value not in mapped:
            mapped.append(value)
    return sorted(mapped)


def _map_efficacy(functions: list[str]) -> list[str]:
    domains: list[str] = []
    for tag in functions:
        key = _normalize_function_tag(tag)
        domain = _EFFICACY_FROM_FUNCTION.get(key)
        if domain and domain not in domains:
            domains.append(domain)
    return sorted(domains)


def _map_comedogenicity(rating: int | None) -> str:
    if rating is None:
        return ""
    if rating == 0:
        return "none"
    if rating <= 2:
        return "low"
    if rating == 3:
        return "moderate"
    if rating >= 4:
        return "high"
    return ""


def _map_irritancy(potential: str) -> str:
    normalized = potential.lower().strip()
    if not normalized:
        return ""
    if normalized == "none":
        return "low"
    if normalized in ("low", "moderate", "high"):
        return normalized
    return ""


def _map_sensitization(is_allergen: bool, allergen_types: list[str]) -> str:
    if is_allergen or allergen_types:
        return "known_allergen"
    return "unknown"


def _parse_ph_range(text: str) -> dict[str, float] | None:
    if not text:
        return None
    match = re.match(
        r"^\s*([\d.]+)\s*-\s*([\d.]+)\s*$",
        text.strip(),
    )
    if not match:
        return None
    try:
        return {"min": float(match.group(1)), "max": float(match.group(2))}
    except ValueError:
        return None


def _map_evidence_quality(score: int | None) -> str:
    if score is None:
        return ""
    if score >= 5:
        return "strong"
    if score >= 3:
        return "moderate"
    if score >= 1:
        return "weak"
    return ""
