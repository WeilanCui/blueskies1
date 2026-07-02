"""Shared target-matching functions for formulation evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from django.db.models import Q, Min

from core.models import Formulation


@dataclass(frozen=True)
class MatchResult:
    """Result of matching a target against a formulation.

    Attributes:
        matched: True if the target matches the formulation.
        best_position: The lowest (best) position of matching ingredient, or None if not matched/unknown.
        total_ingredients: Total ingredient count in the formulation, or None if unknown.
    """
    matched: bool
    best_position: int | None = None
    total_ingredients: int | None = None


def position_factor(result: MatchResult) -> float:
    """Compute position factor from a MatchResult.

    Factor = max(0.3, 1.0 - 0.7 * (position - 1) / max(total - 1, 1))

    - Position 1 (top) → 1.0
    - Last position in multi-ingredient list → 0.3
    - Single-ingredient list → 1.0
    - Missing position or total → 1.0 (fallback to current behavior)

    Args:
        result: MatchResult with position and total data.

    Returns:
        Float factor in range [0.3, 1.0].
    """
    if not result.matched:
        return 1.0

    if result.best_position is None or result.total_ingredients is None:
        return 1.0

    if result.total_ingredients <= 1:
        return 1.0

    # Linear decay: position 1 → 1.0, last → 0.3
    decay = 0.7 * (result.best_position - 1) / (result.total_ingredients - 1)
    return max(0.3, 1.0 - decay)


def matches_compound(formulation: Formulation, compound_id: int) -> MatchResult:
    """Check if formulation has a specific compound, returning position data.

    Args:
        formulation: The formulation to check.
        compound_id: The compound ID to match.

    Returns:
        MatchResult with matched status, best position, and total ingredients.
    """
    matching_positions = formulation.ingredients.filter(
        compound_id=compound_id
    ).aggregate(best_position=Min('position'))

    best_position = matching_positions.get('best_position')
    matched = best_position is not None

    # Only pay for the count when it will actually be used.
    total_ingredients = formulation.ingredients.count() if matched else None

    return MatchResult(
        matched=matched,
        best_position=best_position,
        total_ingredients=total_ingredients,
    )


def matches_chemical_class(
    formulation: Formulation, chemical_class_id: int
) -> MatchResult:
    """Check if formulation has an ingredient in a specific chemical class.

    Args:
        formulation: The formulation to check.
        chemical_class_id: The chemical class ID to match.

    Returns:
        MatchResult with matched status, best position, and total ingredients.
    """
    matching_positions = formulation.ingredients.filter(
        compound__chemical_class_memberships__chemical_class_id=chemical_class_id,
        compound__chemical_class_memberships__is_active=True,
    ).aggregate(best_position=Min('position'))

    best_position = matching_positions.get('best_position')
    matched = best_position is not None

    # Only pay for the count when it will actually be used.
    total_ingredients = formulation.ingredients.count() if matched else None

    return MatchResult(
        matched=matched,
        best_position=best_position,
        total_ingredients=total_ingredients,
    )


def matches_property(formulation: Formulation, property_def_id: int) -> MatchResult:
    """Check if formulation or its ingredients have a specific property.

    Property matches are formulation-wide and don't have position semantics.
    Returns MatchResult with matched status but no position data.

    Args:
        formulation: The formulation to check.
        property_def_id: The property definition ID to match.

    Returns:
        MatchResult with matched status; best_position and total_ingredients are None.
    """
    matched = Formulation.objects.filter(pk=formulation.pk).filter(
        Q(
            property_assertions__property_def_id=property_def_id,
            property_assertions__is_active=True,
        )
        | Q(
            ingredients__compound__property_assertions__property_def_id=(
                property_def_id
            ),
            ingredients__compound__property_assertions__is_active=True,
        )
        | Q(
            ingredients__compound__chemical_class_memberships__is_active=True,
            ingredients__compound__chemical_class_memberships__chemical_class__property_assertions__property_def_id=property_def_id,
            ingredients__compound__chemical_class_memberships__chemical_class__property_assertions__is_active=True,
        )
    ).exists()

    return MatchResult(matched=matched, best_position=None, total_ingredients=None)


def matches_raw_label(formulation: Formulation, raw_label: str) -> MatchResult:
    """Check if formulation matches a raw text search.

    Raw label matches don't have position semantics.
    Returns MatchResult with matched status but no position data.

    Args:
        formulation: The formulation to check.
        raw_label: The text label to search for.

    Returns:
        MatchResult with matched status; best_position and total_ingredients are None.
    """
    label = raw_label.strip()
    if not label:
        return MatchResult(matched=False, best_position=None, total_ingredients=None)

    matched = Formulation.objects.filter(pk=formulation.pk).filter(
        Q(product__name__icontains=label)
        | Q(product__brand__name__icontains=label)
        | Q(version_label__icontains=label)
        | Q(market__icontains=label)
        | Q(made_in__icontains=label)
        | Q(barcode__icontains=label)
        | Q(raw_inci_text__icontains=label)
        | Q(ingredients__raw_text__icontains=label)
        | Q(ingredients__compound__canonical_inci__icontains=label)
        | Q(ingredients__compound__display_name__icontains=label)
    ).exists()

    return MatchResult(matched=matched, best_position=None, total_ingredients=None)


def matches_product_category(formulation: Formulation, category: str) -> MatchResult:
    """Check if formulation's product matches a category (case-insensitive).

    Product category matches don't have position semantics.
    Returns MatchResult with matched status but no position data.

    Args:
        formulation: The formulation to check.
        category: The category to match.

    Returns:
        MatchResult with matched status; best_position and total_ingredients are None.
    """
    if not formulation.product:
        return MatchResult(matched=False, best_position=None, total_ingredients=None)
    if not category or not category.strip():
        return MatchResult(matched=False, best_position=None, total_ingredients=None)

    matched = (
        formulation.product.category.strip().lower()
        == category.strip().lower()
    )

    return MatchResult(matched=matched, best_position=None, total_ingredients=None)
