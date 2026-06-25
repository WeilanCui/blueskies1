from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models.compound import EnrichmentStatus
from core.models.metadata import SourceType
from core.models.product import Product

if TYPE_CHECKING:
    from django.db.models import Manager

    from core.models.daily_checkin import DailyProductUse
    from core.models.interactions import InteractionAssertion
    from core.models.literature_discovery_target import (
        LiteratureDiscoveryEvent,
        LiteratureDiscoveryTarget,
    )
    from core.models.properties import PropertyAssertion
    from core.models.profiles import ProfileConstraint
    from core.models.reaction import ReactionEvent
    from core.models.routine import RoutineItem





class Formulation(models.Model):
    """A specific ingredient-list variant for a product."""

    id: int
    product_id: int
    ingredients: Manager[FormulationIngredient]
    literature_discovery_targets: Manager[LiteratureDiscoveryTarget]
    literature_discovery_events: Manager[LiteratureDiscoveryEvent]
    property_assertions: Manager[PropertyAssertion]
    profile_constraints: Manager[ProfileConstraint]
    interaction_assertions: Manager[InteractionAssertion]
    daily_product_uses: Manager[DailyProductUse]
    routine_items: Manager[RoutineItem]
    reaction_events: Manager[ReactionEvent]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="formulations",
    )
    sku = models.CharField(max_length=128, blank=True)
    barcode = models.CharField(max_length=64, blank=True, unique=True, null=True)
    enrichment_status = models.CharField(
        max_length=32,
        choices=EnrichmentStatus.choices,
        default=EnrichmentStatus.PENDING,
    )
    raw_inci_text = models.TextField(blank=True)
    source = models.CharField(max_length=64, blank=True)
    source_ref = models.CharField(max_length=512, blank=True)
    market = models.CharField(max_length=64, blank=True)
    made_in = models.CharField(max_length=128, blank=True)
    version_label = models.CharField(max_length=128, blank=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    inci_analysis = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product__brand__name", "product__name", "market", "version_label", "id"]

    @property
    def name(self) -> str:
        return self.product.name

    @property
    def brand(self) -> str:
        if self.product.brand_id is None:
            return ""
        return self.product.brand.name

    def __str__(self) -> str:
        variant_bits = [self.version_label, self.market, self.made_in, self.barcode]
        variant = " / ".join(bit for bit in variant_bits if bit)
        if variant:
            return f"{self.product} ({variant})"
        return str(self.product)


class FormulationIngredient(models.Model):
    """Ordered INCI list entry — position proxies concentration."""

    id: int
    compound_id: int | None

    formulation = models.ForeignKey(
        Formulation,
        on_delete=models.CASCADE,
        related_name="ingredients",
    )
    position = models.PositiveSmallIntegerField()
    raw_text = models.CharField(max_length=512)
    compound = models.ForeignKey(
        "core.Compound",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="formulation_appearances",
    )
    parse_status = models.CharField(
        max_length=32,
        choices=[
            ("matched", "Matched"),
            ("unmatched", "Unmatched"),
            ("ambiguous", "Ambiguous"),
        ],
        default="unmatched",
    )
    is_key_active = models.BooleanField(default=False)
    active_note = models.TextField(blank=True)
    functional_classes_override = models.JSONField(default=list, blank=True)
    function_override_source = models.CharField(
        max_length=32,
        choices=SourceType.choices,
        blank=True,
    )
    function_override_confidence = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    function_override_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["formulation", "position"],
                name="unique_formulation_ingredient_position",
            )
        ]

    def __str__(self) -> str:
        return f"{self.position}. {self.raw_text}"

    @property
    def inherited_functional_classes(self) -> list[str]:
        if self.compound_id is None:
            return []

        values: list[str] = []
        assertions = self.compound.property_assertions.filter(
            property_def__key="functional_class",
            is_active=True,
        )
        for assertion in assertions:
            raw_value = assertion.value_json
            if isinstance(raw_value, list):
                values.extend(str(value) for value in raw_value if value)
            elif assertion.value_text:
                values.append(assertion.value_text)

        return list(dict.fromkeys(values))

    @property
    def effective_functional_classes(self) -> list[str]:
        if self.functional_classes_override:
            return [str(value) for value in self.functional_classes_override if value]
        return self.inherited_functional_classes

    @property
    def is_function_override(self) -> bool:
        return bool(self.functional_classes_override)
