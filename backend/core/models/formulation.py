from django.db import models
from django.db.models.functions import Lower

from core.models.compound import EnrichmentStatus


class Product(models.Model):
    """A commercial skincare product that can have multiple formula variants."""

    brand = models.CharField(max_length=256, blank=True)
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
        ordering = ["brand", "name"]
        constraints = [
            models.UniqueConstraint(
                Lower("brand"),
                Lower("name"),
                name="unique_product_brand_name_ci",
            )
        ]

    def __str__(self) -> str:
        if self.display_name:
            return self.display_name
        if self.brand:
            return f"{self.brand} {self.name}"
        return self.name


class Formulation(models.Model):
    """A specific ingredient-list variant for a product."""

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product__brand", "product__name", "market", "version_label", "id"]

    @property
    def name(self) -> str:
        return self.product.name

    @property
    def brand(self) -> str:
        return self.product.brand

    def __str__(self) -> str:
        variant_bits = [self.version_label, self.market, self.made_in, self.barcode]
        variant = " / ".join(bit for bit in variant_bits if bit)
        if variant:
            return f"{self.product} ({variant})"
        return str(self.product)


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
    is_key_active = models.BooleanField(default=False)
    active_note = models.TextField(blank=True)

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
