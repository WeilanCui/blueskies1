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


class LiteratureDiscoveryTargetType(models.TextChoices):
    COMPOUND = "compound", "Compound"
    FORMULATION = "formulation", "Formulation"
    PRODUCT = "product", "Product"


class LiteratureDiscoveryEventType(models.TextChoices):
    COMPOUND_CREATED_FROM_PRODUCT = (
        "compound.created_from_product",
        "Compound created from product",
    )
    COMPOUND_CREATED_FROM_FORMULATION = (
        "compound.created_from_formulation",
        "Compound created from formulation",
    )
    COMPOUND_RESOLVED_FROM_INCI = (
        "compound.resolved_from_inci",
        "Compound resolved from INCI",
    )
    MIXTURE_CREATED_FROM_PRODUCT = (
        "mixture.created_from_product",
        "Mixture created from product",
    )
    MIXTURE_CREATED_FROM_FORMULATION = (
        "mixture.created_from_formulation",
        "Mixture created from formulation",
    )
    MIXTURE_RESOLVED_FROM_INCI = (
        "mixture.resolved_from_inci",
        "Mixture resolved from INCI",
    )
    FORMULATION_CREATED = "formulation.created", "Formulation created"
    PRODUCT_CREATED = "product.created", "Product created"


class LiteratureDiscoveryEventStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSED = "processed", "Processed"
    FAILED = "failed", "Failed"
    SKIPPED = "skipped", "Skipped"


ACTIVE_DISCOVERY_STATUSES = (
    DiscoveryTargetStatus.PENDING,
    DiscoveryTargetStatus.RUNNING,
)

DEFAULT_MAX_DISCOVERY_ATTEMPTS = 3

DEFAULT_DISCOVERY_PRIORITY = 0
PRODUCT_FORMULATION_DISCOVERY_PRIORITY = 10


class LiteratureDiscoveryTarget(models.Model):
    """Queued literature discovery work item for one searchable entity."""

    target_type = models.CharField(
        max_length=32,
        choices=LiteratureDiscoveryTargetType.choices,
        default=LiteratureDiscoveryTargetType.COMPOUND,
    )
    compound = models.ForeignKey(
        Compound,
        on_delete=models.CASCADE,
        related_name="literature_discovery_targets",
        null=True,
        blank=True,
    )
    formulation = models.ForeignKey(
        "core.Formulation",
        on_delete=models.CASCADE,
        related_name="literature_discovery_targets",
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        "core.Product",
        on_delete=models.CASCADE,
        related_name="literature_discovery_targets",
        null=True,
        blank=True,
    )
    search_label = models.CharField(max_length=512, blank=True)
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
    priority = models.IntegerField(default=DEFAULT_DISCOVERY_PRIORITY)
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
            models.CheckConstraint(
                check=(
                    Q(
                        target_type=LiteratureDiscoveryTargetType.COMPOUND,
                        compound__isnull=False,
                        formulation__isnull=True,
                        product__isnull=True,
                    )
                    | Q(
                        target_type=LiteratureDiscoveryTargetType.FORMULATION,
                        compound__isnull=True,
                        formulation__isnull=False,
                        product__isnull=True,
                    )
                    | Q(
                        target_type=LiteratureDiscoveryTargetType.PRODUCT,
                        compound__isnull=True,
                        formulation__isnull=True,
                        product__isnull=False,
                    )
                ),
                name="literature_discovery_target_exactly_one_target",
            ),
            models.UniqueConstraint(
                fields=["compound"],
                condition=Q(
                    status__in=[
                        DiscoveryTargetStatus.PENDING,
                        DiscoveryTargetStatus.RUNNING,
                    ]
                )
                & Q(target_type=LiteratureDiscoveryTargetType.COMPOUND)
                & Q(compound__isnull=False),
                name="unique_active_literature_discovery_per_compound",
            ),
            models.UniqueConstraint(
                fields=["formulation"],
                condition=Q(
                    status__in=[
                        DiscoveryTargetStatus.PENDING,
                        DiscoveryTargetStatus.RUNNING,
                    ]
                )
                & Q(target_type=LiteratureDiscoveryTargetType.FORMULATION)
                & Q(formulation__isnull=False),
                name="unique_active_literature_discovery_per_formulation",
            ),
            models.UniqueConstraint(
                fields=["product"],
                condition=Q(
                    status__in=[
                        DiscoveryTargetStatus.PENDING,
                        DiscoveryTargetStatus.RUNNING,
                    ]
                )
                & Q(target_type=LiteratureDiscoveryTargetType.PRODUCT)
                & Q(product__isnull=False),
                name="unique_active_literature_discovery_per_product",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "priority", "created_at"],
                name="core_litera_status_8a0f0d_idx",
            ),
            models.Index(
                fields=["target_type", "status", "created_at"],
                name="core_litdt_ttype_status_idx",
            ),
        ]

    @property
    def target_id(self) -> int | None:
        if self.target_type == LiteratureDiscoveryTargetType.COMPOUND:
            return self.compound_id
        if self.target_type == LiteratureDiscoveryTargetType.FORMULATION:
            return self.formulation_id
        if self.target_type == LiteratureDiscoveryTargetType.PRODUCT:
            return self.product_id
        return None

    def resolved_search_label(self) -> str:
        if self.target_type == LiteratureDiscoveryTargetType.COMPOUND and self.compound:
            return self.compound.display_name or self.compound.canonical_inci
        if (
            self.target_type == LiteratureDiscoveryTargetType.FORMULATION
            and self.formulation
        ):
            return str(self.formulation)
        if self.target_type == LiteratureDiscoveryTargetType.PRODUCT and self.product:
            return self.product.display_name or self.product.name
        return ""

    def save(self, *args, **kwargs):
        if not self.search_label:
            self.search_label = self.resolved_search_label()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        label = self.search_label or self.resolved_search_label() or "Unknown target"
        return f"{label} ({self.status})"


class LiteratureDiscoveryEvent(models.Model):
    """Durable outbox event that becomes a literature discovery work item."""

    event_type = models.CharField(
        max_length=64,
        choices=LiteratureDiscoveryEventType.choices,
    )
    status = models.CharField(
        max_length=16,
        choices=LiteratureDiscoveryEventStatus.choices,
        default=LiteratureDiscoveryEventStatus.PENDING,
    )
    target_type = models.CharField(
        max_length=32,
        choices=LiteratureDiscoveryTargetType.choices,
        default=LiteratureDiscoveryTargetType.COMPOUND,
    )
    compound = models.ForeignKey(
        Compound,
        on_delete=models.CASCADE,
        related_name="literature_discovery_events",
        null=True,
        blank=True,
    )
    formulation = models.ForeignKey(
        "core.Formulation",
        on_delete=models.CASCADE,
        related_name="literature_discovery_events",
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        "core.Product",
        on_delete=models.CASCADE,
        related_name="literature_discovery_events",
        null=True,
        blank=True,
    )
    reason = models.CharField(
        max_length=32,
        choices=DiscoveryReason.choices,
        default=DiscoveryReason.NEW_COMPOUND,
    )
    priority = models.IntegerField(default=DEFAULT_DISCOVERY_PRIORITY)
    search_label = models.CharField(max_length=512, blank=True)
    triggered_by = models.CharField(max_length=128, blank=True)
    source_ref = models.CharField(max_length=512, blank=True)
    dedupe_key = models.CharField(
        max_length=512,
        blank=True,
        null=True,
        unique=True,
    )
    payload = models.JSONField(default=dict, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(
                        target_type=LiteratureDiscoveryTargetType.COMPOUND,
                        compound__isnull=False,
                        formulation__isnull=True,
                        product__isnull=True,
                    )
                    | Q(
                        target_type=LiteratureDiscoveryTargetType.FORMULATION,
                        compound__isnull=True,
                        formulation__isnull=False,
                        product__isnull=True,
                    )
                    | Q(
                        target_type=LiteratureDiscoveryTargetType.PRODUCT,
                        compound__isnull=True,
                        formulation__isnull=True,
                        product__isnull=False,
                    )
                ),
                name="literature_discovery_event_exactly_one_target",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "created_at"],
                name="core_litde_status_created_idx",
            ),
            models.Index(
                fields=["target_type", "status", "created_at"],
                name="core_litde_ttype_status_idx",
            ),
        ]

    @property
    def target_id(self) -> int | None:
        if self.target_type == LiteratureDiscoveryTargetType.COMPOUND:
            return self.compound_id
        if self.target_type == LiteratureDiscoveryTargetType.FORMULATION:
            return self.formulation_id
        if self.target_type == LiteratureDiscoveryTargetType.PRODUCT:
            return self.product_id
        return None

    def resolved_search_label(self) -> str:
        if self.target_type == LiteratureDiscoveryTargetType.COMPOUND and self.compound:
            return self.compound.display_name or self.compound.canonical_inci
        if (
            self.target_type == LiteratureDiscoveryTargetType.FORMULATION
            and self.formulation
        ):
            return str(self.formulation)
        if self.target_type == LiteratureDiscoveryTargetType.PRODUCT and self.product:
            return self.product.display_name or self.product.name
        return ""

    def save(self, *args, **kwargs):
        if not self.search_label:
            self.search_label = self.resolved_search_label()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        label = self.search_label or self.resolved_search_label() or "Unknown target"
        return f"{self.event_type}: {label}"
