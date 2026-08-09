"""Data confidence scoring for formulations in recommendations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.models.compound import EnrichmentStatus

if TYPE_CHECKING:
    from core.models import Formulation

# Confidence band thresholds
CONFIDENCE_HIGH = 0.8
CONFIDENCE_MEDIUM = 0.4


def data_confidence(formulation: Formulation) -> float:
    """
    Compute the fraction of a formulation's ingredients resolved to compounds.

    Args:
        formulation: The formulation to score.

    Returns:
        A float in [0, 1] representing ingredient resolution confidence.
        - 0.0 if no ingredients exist
        - capped at 0.5 if enrichment_status is EnrichmentStatus.PENDING
        - otherwise resolved/total where resolved = matched + compound_id not None
    """
    # Use prefetched ingredients if available (from queryset.prefetch_related("ingredients"))
    ingredients = list(formulation.ingredients.all())
    total = len(ingredients)

    if total == 0:
        return 0.0

    resolved = sum(
        1
        for ing in ingredients
        if ing.parse_status == "matched" and ing.compound_id is not None
    )

    conf = resolved / total

    # Cap at 0.5 if enrichment is still pending
    if formulation.enrichment_status == EnrichmentStatus.PENDING:
        conf = min(conf, 0.5)

    return conf


def confidence_band(value: float) -> str:
    """
    Map a confidence value to a coarse band.

    Args:
        value: A float in [0, 1].

    Returns:
        "high" if value >= 0.8, "medium" if value >= 0.4, "low" otherwise.
    """
    if value >= CONFIDENCE_HIGH:
        return "high"
    if value >= CONFIDENCE_MEDIUM:
        return "medium"
    return "low"
