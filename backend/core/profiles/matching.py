"""Shared target-matching functions for formulation evaluation."""

from django.db.models import Q

from core.models import Formulation


def matches_compound(formulation: Formulation, compound_id: int) -> bool:
    """Check if formulation has a specific compound."""
    return formulation.ingredients.filter(compound_id=compound_id).exists()


def matches_chemical_class(
    formulation: Formulation, chemical_class_id: int
) -> bool:
    """Check if formulation has an ingredient in a specific chemical class."""
    return formulation.ingredients.filter(
        compound__chemical_class_memberships__chemical_class_id=chemical_class_id,
        compound__chemical_class_memberships__is_active=True,
    ).exists()


def matches_property(formulation: Formulation, property_def_id: int) -> bool:
    """Check if formulation or its ingredients have a specific property."""
    return Formulation.objects.filter(pk=formulation.pk).filter(
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


def matches_raw_label(formulation: Formulation, raw_label: str) -> bool:
    """Check if formulation matches a raw text search."""
    label = raw_label.strip()
    if not label:
        return False

    return Formulation.objects.filter(pk=formulation.pk).filter(
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


def matches_product_category(formulation: Formulation, category: str) -> bool:
    """Check if formulation's product matches a category (case-insensitive)."""
    if not formulation.product:
        return False
    if not category or not category.strip():
        return False
    return (
        formulation.product.category.strip().lower()
        == category.strip().lower()
    )
