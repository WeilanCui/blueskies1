from django.db import models

from skinconcerns.models.choices import RecommendationPolicy, TriggerSeverity
from skinconcerns.normalization import normalize_search_text


class ConcernReferralTrigger(models.Model):
    """Phrase or signal that should change recommendation routing."""

    concern = models.ForeignKey(
        "skinconcerns.SkinConcern",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="referral_triggers",
    )
    key = models.SlugField(max_length=128, unique=True)
    trigger_text = models.CharField(max_length=256)
    normalized_trigger = models.CharField(max_length=256, unique=True, editable=False)
    description = models.TextField(blank=True)
    severity = models.CharField(
        max_length=16,
        choices=TriggerSeverity.choices,
        default=TriggerSeverity.URGENT,
    )
    policy_override = models.CharField(
        max_length=32,
        choices=RecommendationPolicy.choices,
        default=RecommendationPolicy.SUPPRESS,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["severity", "trigger_text"]
        indexes = [
            models.Index(fields=["severity", "is_active"]),
        ]

    def save(self, *args, **kwargs):
        self.normalized_trigger = normalize_search_text(self.trigger_text)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.trigger_text
