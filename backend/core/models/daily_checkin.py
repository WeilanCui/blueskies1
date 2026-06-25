from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models.profile import Profile
from core.models.skin_profile import SkinProfile


class RoutineTimeOfDay(models.TextChoices):
    AM = "am", "AM"
    PM = "pm", "PM"
    ANY = "any", "Any time"
    CUSTOM = "custom", "Custom"


class RoutineStep(models.TextChoices):
    CLEANSER = "cleanser", "Cleanser"
    TONER_ESSENCE = "toner_essence", "Toner / essence"
    TREATMENT = "treatment", "Treatment"
    MOISTURIZER = "moisturizer", "Moisturizer"
    SPF = "spf", "SPF"
    MASK = "mask", "Mask"
    EXFOLIANT = "exfoliant", "Exfoliant"
    EYE_CARE = "eye_care", "Eye care"
    OTHER = "other", "Other"


class DailyCheckIn(models.Model):
    """A dated skin and lifestyle record for day-to-day tracking."""

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="daily_checkins",
    )
    skin_profile = models.ForeignKey(
        SkinProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="daily_checkins",
    )
    checkin_date = models.DateField()
    skin_feel = models.CharField(max_length=64, blank=True)
    skin_notes = models.TextField(blank=True)
    symptoms = models.JSONField(default=list, blank=True)
    suspected_triggers = models.JSONField(default=list, blank=True)
    sleep_hours = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
    )
    stress_level = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    hydration_level = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    dryness_level = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    oiliness_level = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    redness_level = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    irritation_level = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    breakout_count = models.PositiveSmallIntegerField(null=True, blank=True)
    am_routine_completed = models.BooleanField(null=True, blank=True)
    pm_routine_completed = models.BooleanField(null=True, blank=True)
    weather = models.CharField(max_length=128, blank=True)
    cycle_phase = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-checkin_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "checkin_date"],
                name="unique_profile_daily_checkin",
            )
        ]

    def __str__(self) -> str:
        return f"{self.profile} check-in on {self.checkin_date}"


class DailyProductUse(models.Model):
    """Product or formulation used as part of a daily check-in."""

    checkin = models.ForeignKey(
        DailyCheckIn,
        on_delete=models.CASCADE,
        related_name="product_uses",
    )
    formulation = models.ForeignKey(
        "core.Formulation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="daily_product_uses",
    )
    product = models.ForeignKey(
        "core.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="daily_product_uses",
    )
    routine = models.ForeignKey(
        "core.Routine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="daily_product_uses",
    )
    routine_item = models.ForeignKey(
        "core.RoutineItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="daily_product_uses",
    )
    raw_product_name = models.CharField(max_length=512, blank=True)
    time_of_day = models.CharField(
        max_length=16,
        choices=RoutineTimeOfDay.choices,
        default=RoutineTimeOfDay.ANY,
    )
    routine_step = models.CharField(
        max_length=32,
        choices=RoutineStep.choices,
        default=RoutineStep.OTHER,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["time_of_day", "routine_step", "created_at"]

    def __str__(self) -> str:
        product = self.formulation or self.raw_product_name or "Product"
        return f"{product} on {self.checkin.checkin_date}"
