from django.db import models
from django.db.models import Q

from core.models.compound import Compound


class DiscoveryReason(models.TextChoices):
    NEW_COMPOUND = "new_compound", "New compound"
    NEW_MIXTURE = "new_mixture", "New mixture"
    MANUAL_REVIEW = "manual_review", "Manual review"
    RETRY = "retry", "Retry"


class DiscoveryTargetStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    SKIPPED = "skipped", "Skipped"


ACTIVE_DISCOVERY_STATUSES = (
    DiscoveryTargetStatus.PENDING,
    DiscoveryTargetStatus.RUNNING,
)

DEFAULT_MAX_DISCOVERY_ATTEMPTS = 3


class LiteratureDiscoveryTarget(models.Model):
    """Queued ingredient-level literature discovery work for a compound."""

    compound = models.ForeignKey(
        Compound,
        on_delete=models.CASCADE,
        related_name="literature_discovery_targets",
    )
    reason = models.CharField(
        max_length=32,
        choices=DiscoveryReason.choices,
        default=DiscoveryReason.NEW_COMPOUND,
    )
    status = models.CharField(
        max_length=16,
        choices=DiscoveryTargetStatus.choices,
        default=DiscoveryTargetStatus.PENDING,
    )
    priority = models.IntegerField(default=0)
    attempt_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    triggered_by = models.CharField(max_length=128, blank=True)
    source_ref = models.CharField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["compound"],
                condition=Q(
                    status__in=[
                        DiscoveryTargetStatus.PENDING,
                        DiscoveryTargetStatus.RUNNING,
                    ]
                ),
                name="unique_active_literature_discovery_per_compound",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "priority", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.compound.canonical_inci} ({self.status})"
