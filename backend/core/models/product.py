from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models
from django.db.models.functions import Lower

from core.models.brand import Brand

if TYPE_CHECKING:
    from django.db.models import Manager

    from core.models.daily_checkin import DailyProductUse
    from core.models.formulation import Formulation
    from literature.models.discovery_target import (
        LiteratureDiscoveryEvent,
        LiteratureDiscoveryTarget,
    )
    from core.models.reaction import ReactionEvent
    from core.models.routine import RoutineItem


class Product(models.Model):
    """A commercial skincare product that can have multiple formula variants."""

    id: int
    brand_id: int | None
    formulations: Manager[Formulation]
    literature_discovery_targets: Manager[LiteratureDiscoveryTarget]
    literature_discovery_events: Manager[LiteratureDiscoveryEvent]
    routine_items: Manager[RoutineItem]
    daily_product_uses: Manager[DailyProductUse]
    reaction_events: Manager[ReactionEvent]

    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    name = models.CharField(max_length=512)
    display_name = models.CharField(max_length=512, blank=True)
    category = models.CharField(max_length=128, blank=True)
    description = models.TextField(blank=True)
    image_url = models.URLField(max_length=1024, blank=True)
    source = models.CharField(max_length=64, blank=True)
    source_ref = models.CharField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["brand__name", "name"]
        constraints = [
            models.UniqueConstraint(
                models.F("brand"),
                Lower("name"),
                name="unique_product_brand_name_ci",
            )
        ]

    def __str__(self) -> str:
        if self.display_name:
            return self.display_name
        if self.brand_id:  # pyright: ignore[reportAttributeAccessIssue]
            return f"{self.brand} {self.name}"
        return self.name
