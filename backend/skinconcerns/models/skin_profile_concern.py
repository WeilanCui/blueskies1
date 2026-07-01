from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from skinconcerns.models.choices import ProfileConcernSource


class SkinProfileConcern(models.Model):
    """Normalized selected or detected concern for a skin profile snapshot."""

    skin_profile = models.ForeignKey(
        "core.SkinProfile",
        on_delete=models.CASCADE,
        related_name="concerns",
    )
    concern = models.ForeignKey(
        "skinconcerns.SkinConcern",
        on_delete=models.CASCADE,
        related_name="profile_selections",
    )
    source = models.CharField(
        max_length=32,
        choices=ProfileConcernSource.choices,
        default=ProfileConcernSource.USER_SELECTED,
    )
    confidence = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    raw_text = models.CharField(max_length=256, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["skin_profile", "concern__group", "concern__display_name"]
        indexes = [
            models.Index(fields=["skin_profile", "is_active"]),
            models.Index(fields=["source", "is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["skin_profile", "concern"],
                condition=Q(is_active=True),
                name="unique_active_skin_profile_concern",
            )
        ]

    def __str__(self) -> str:
        return f"{self.skin_profile}: {self.concern}"
