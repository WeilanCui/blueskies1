from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models
from django.db.models.functions import Lower

if TYPE_CHECKING:
    from django.db.models import Manager

    from core.models.product import Product


class Brand(models.Model):
    """A commercial skincare brand that owns one or more products."""

    products: Manager[Product]

    name = models.CharField(max_length=256)
    display_name = models.CharField(max_length=256, blank=True)
    description = models.TextField(blank=True)
    website_url = models.URLField(max_length=1024, blank=True)
    image_url = models.URLField(max_length=1024, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="unique_brand_name_ci",
            )
        ]

    def __str__(self) -> str:
        return self.display_name or self.name

    @classmethod
    def get_or_create_by_name(cls, name: str) -> Brand | None:
        cleaned = name.strip()
        if not cleaned:
            return None

        brand = cls.objects.filter(name__iexact=cleaned).first()
        if brand is not None:
            return brand

        return cls.objects.create(name=cleaned)
