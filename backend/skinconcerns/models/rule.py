from django.core.exceptions import ValidationError
from django.db import models

from skinconcerns.models.choices import RuleKind, RuleTargetType


class ConcernRule(models.Model):
    """Recommendation or routing rule for a skin concern."""

    concern = models.ForeignKey(
        "skinconcerns.SkinConcern",
        on_delete=models.CASCADE,
        related_name="rules",
    )
    key = models.SlugField(max_length=128, unique=True)
    label = models.CharField(max_length=256)
    rule_kind = models.CharField(
        max_length=16,
        choices=RuleKind.choices,
        default=RuleKind.RECOMMEND,
    )
    target_type = models.CharField(
        max_length=32,
        choices=RuleTargetType.choices,
        default=RuleTargetType.PRODUCT_CATEGORY,
    )
    product_category = models.CharField(max_length=128, blank=True)
    chemical_class = models.ForeignKey(
        "core.ChemicalClass",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="concern_rules",
    )
    compound = models.ForeignKey(
        "core.Compound",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="concern_rules",
    )
    property_def = models.ForeignKey(
        "core.PropertyDefinition",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="concern_rules",
    )
    raw_target = models.CharField(max_length=256, blank=True)
    weight = models.IntegerField(default=10)
    rationale = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["concern__slug", "rule_kind", "label"]
        indexes = [
            models.Index(fields=["rule_kind", "target_type", "is_active"]),
            models.Index(fields=["concern", "is_active"]),
        ]

    def clean(self) -> None:
        targets = {
            RuleTargetType.PRODUCT_CATEGORY: bool(self.product_category.strip()),
            RuleTargetType.CHEMICAL_CLASS: bool(self.chemical_class_id),
            RuleTargetType.COMPOUND: bool(self.compound_id),
            RuleTargetType.PROPERTY: bool(self.property_def_id),
            RuleTargetType.FREE_TEXT: bool(self.raw_target.strip()),
        }
        if not targets[self.target_type]:
            raise ValidationError(
                {"target_type": "Target value must match the selected target type."}
            )
        if sum(targets.values()) != 1:
            raise ValidationError("Set exactly one rule target.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def target_label(self) -> str:
        target = self.chemical_class or self.compound or self.property_def
        if target is not None:
            return str(target)
        return self.product_category or self.raw_target

    def __str__(self) -> str:
        return f"{self.concern}: {self.rule_kind} {self.target_label}"
