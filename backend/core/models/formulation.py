from django.db import models

from core.models.compound import EnrichmentStatus


class Formulation(models.Model):
    """A product or master formula sheet."""

    name = models.CharField(max_length=512)
    brand = models.CharField(max_length=256, blank=True)
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class FormulationIngredient(models.Model):
    """Ordered INCI list entry — position proxies concentration."""

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
