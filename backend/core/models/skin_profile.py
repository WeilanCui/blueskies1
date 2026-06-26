from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.models.profile import Profile


class SkinType(models.TextChoices):
    NORMAL = "normal", "Normal"
    DRY = "dry", "Dry"
    OILY = "oily", "Oily"
    COMBINATION = "combination", "Combination"
    SENSITIVE = "sensitive", "Sensitive"
    UNKNOWN = "unknown", "Unknown"


class FitzpatrickSkinType(models.TextChoices):
    TYPE_I = "type_i", "Type I"
    TYPE_II = "type_ii", "Type II"
    TYPE_III = "type_iii", "Type III"
    TYPE_IV = "type_iv", "Type IV"
    TYPE_V = "type_v", "Type V"
    TYPE_VI = "type_vi", "Type VI"
    NOT_PROVIDED = "not_provided", "Not provided"


class PregnancyStatus(models.TextChoices):
    NOT_PROVIDED = "not_provided", "Not provided"
    NOT_APPLICABLE = "not_applicable", "Not applicable"
    TRYING = "trying", "Trying to conceive"
    PREGNANT = "pregnant", "Pregnant"
    NURSING = "nursing", "Nursing"


class SkinProfile(models.Model):
    """Versioned skin-state snapshot used for matching and trend history."""

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="skin_profiles",
    )
    label = models.CharField(max_length=128, blank=True)
    is_current = models.BooleanField(default=False)
    captured_at = models.DateTimeField(default=timezone.now)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    skin_types = models.JSONField(default=list, blank=True)
    fitzpatrick_skin_type = models.CharField(
        max_length=32,
        choices=FitzpatrickSkinType.choices,
        default=FitzpatrickSkinType.NOT_PROVIDED,
    )
    primary_concerns = models.JSONField(default=list, blank=True)
    goals = models.JSONField(default=list, blank=True)
    current_routine = models.JSONField(default=dict, blank=True)
    pregnancy_status = models.CharField(
        max_length=32,
        choices=PregnancyStatus.choices,
        default=PregnancyStatus.NOT_PROVIDED,
    )
    baseline_sensitivity = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    climate = models.CharField(max_length=64, blank=True)
    routine_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-captured_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["profile"],
                condition=Q(is_current=True),
                name="unique_current_skin_profile",
            )
        ]

    def __str__(self) -> str:
        label = self.label or self.captured_at.date().isoformat()
        return f"{self.profile} skin profile ({label})"

    @property
    def primary_skin_type(self) -> str:
        return (self.skin_types or [SkinType.UNKNOWN])[0]
