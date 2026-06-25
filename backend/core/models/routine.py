from django.core.exceptions import ValidationError
from django.db import models

from core.models.daily_checkin import RoutineStep, RoutineTimeOfDay
from core.models.profiles import Profile


class Routine(models.Model):
    """A reusable profile-owned skincare routine template."""

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="routines",
    )
    name = models.CharField(max_length=128)
    time_of_day = models.CharField(
        max_length=16,
        choices=RoutineTimeOfDay.choices,
        default=RoutineTimeOfDay.ANY,
    )
    custom_time_label = models.CharField(max_length=128, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["profile", "time_of_day", "name", "id"]
        indexes = [
            models.Index(fields=["profile", "time_of_day", "is_active"]),
        ]

    def clean(self) -> None:
        if self.time_of_day == RoutineTimeOfDay.CUSTOM and not self.custom_time_label.strip():
            raise ValidationError("Custom routines need a custom_time_label.")

    def __str__(self) -> str:
        return f"{self.profile}: {self.name}"


class RoutineItem(models.Model):
    """An ordered product or manual entry in a routine template."""

    routine = models.ForeignKey(
        Routine,
        on_delete=models.CASCADE,
        related_name="items",
    )
    position = models.PositiveSmallIntegerField()
    routine_step = models.CharField(
        max_length=32,
        choices=RoutineStep.choices,
        default=RoutineStep.OTHER,
    )
    custom_step_label = models.CharField(max_length=128, blank=True)
    product = models.ForeignKey(
        "core.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="routine_items",
    )
    formulation = models.ForeignKey(
        "core.Formulation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="routine_items",
    )
    raw_product_name = models.CharField(max_length=512, blank=True)
    usage_notes = models.TextField(blank=True)
    frequency = models.CharField(max_length=128, blank=True)
    schedule = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["routine", "position"],
                name="unique_routine_item_position",
            )
        ]

    def clean(self) -> None:
        if self.formulation_id and self.product_id and self.formulation.product_id != self.product_id:  # pyright: ignore[reportAttributeAccessIssue]
            raise ValidationError("Formulation must belong to the selected product.")
        if not self.product_id and not self.formulation_id and not self.raw_product_name.strip():  # pyright: ignore[reportAttributeAccessIssue]
            raise ValidationError("Routine item needs a product, formulation, or raw_product_name.")

    @property
    def display_name(self) -> str:
        if self.product_id:  # pyright: ignore[reportAttributeAccessIssue]
            return self.product.display_name or self.product.name
        if self.formulation_id:  # pyright: ignore[reportAttributeAccessIssue]
            return self.formulation.product.display_name or self.formulation.product.name
        return self.raw_product_name

    def __str__(self) -> str:
        return f"{self.position}. {self.display_name}"
