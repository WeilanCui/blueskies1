from __future__ import annotations

from django.db import models
from django.utils import timezone

from core.models.profile import Profile


class ReactionSeverity(models.TextChoices):
    MILD = "mild", "Mild"
    MODERATE = "moderate", "Moderate"
    SEVERE = "severe", "Severe"


class ReactionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    RESOLVED = "resolved", "Resolved"


class ReactionEvent(models.Model):
    """A logged adverse reaction or sensitivity event."""

    id: int
    daily_checkin_id: int | None
    routine_id: int | None
    routine_item_id: int | None
    product_id: int | None
    formulation_id: int | None

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="reaction_events",
    )
    daily_checkin = models.ForeignKey(
        "core.DailyCheckIn",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reaction_events",
    )
    routine = models.ForeignKey(
        "core.Routine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reaction_events",
    )
    routine_item = models.ForeignKey(
        "core.RoutineItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reaction_events",
    )
    product = models.ForeignKey(
        "core.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reaction_events",
    )
    formulation = models.ForeignKey(
        "core.Formulation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reaction_events",
    )
    title = models.CharField(max_length=160)
    severity = models.CharField(
        max_length=16,
        choices=ReactionSeverity.choices,
        default=ReactionSeverity.MILD,
    )
    status = models.CharField(
        max_length=16,
        choices=ReactionStatus.choices,
        default=ReactionStatus.ACTIVE,
    )
    occurred_on = models.DateField(default=timezone.localdate)
    resolved_on = models.DateField(null=True, blank=True)
    symptoms = models.JSONField(default=list, blank=True)
    suspected_trigger = models.CharField(max_length=512, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-occurred_on", "-created_at"]
        indexes = [
            models.Index(fields=["profile", "status", "occurred_on"]),
        ]

    def __str__(self) -> str:
        return f"{self.profile}: {self.title}"
