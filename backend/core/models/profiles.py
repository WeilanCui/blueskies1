from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class ProfileVisibility(models.TextChoices):
    PRIVATE = "private", "Private"
    UNLISTED = "unlisted", "Unlisted"
    PUBLIC = "public", "Public"


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


class ProfileConstraintKind(models.TextChoices):
    ALLERGY = "allergy", "Allergy"
    SENSITIVITY = "sensitivity", "Sensitivity"
    AVOID = "avoid", "Avoid"
    PREFER = "prefer", "Prefer"
    CAUTION = "caution", "Caution"
    GOAL_SUPPORT = "goal_support", "Goal support"
    LIFESTYLE = "lifestyle", "Lifestyle"


class ConstraintEnforcement(models.TextChoices):
    EXCLUDE = "exclude", "Exclude"
    WARN = "warn", "Warn"
    PENALIZE = "penalize", "Penalize"
    BOOST = "boost", "Boost"
    INFORM = "inform", "Inform"


class ConstraintSeverity(models.TextChoices):
    LOW = "low", "Low"
    MODERATE = "moderate", "Moderate"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class Profile(models.Model):
    """Profile aggregate root linked one-to-one with Django auth.User."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    handle = models.SlugField(max_length=64, unique=True, null=True, blank=True)
    display_name = models.CharField(max_length=128, blank=True)
    bio = models.TextField(blank=True)
    pronouns = models.CharField(max_length=64, blank=True)
    avatar_url = models.URLField(max_length=1024, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    locale = models.CharField(max_length=16, blank=True)
    visibility = models.CharField(
        max_length=16,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.PRIVATE,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self) -> str:
        return self.display_name or self.handle or self.user.get_username()


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
    skin_type = models.CharField(
        max_length=32,
        choices=SkinType.choices,
        default=SkinType.UNKNOWN,
    )
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


class ProfileConstraint(models.Model):
    """A flexible personal rule used by recommendation and safety evaluators."""

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="constraints",
    )
    kind = models.CharField(
        max_length=32,
        choices=ProfileConstraintKind.choices,
        default=ProfileConstraintKind.SENSITIVITY,
    )
    enforcement = models.CharField(
        max_length=16,
        choices=ConstraintEnforcement.choices,
        default=ConstraintEnforcement.WARN,
    )
    severity = models.CharField(
        max_length=16,
        choices=ConstraintSeverity.choices,
        default=ConstraintSeverity.MODERATE,
    )
    compound = models.ForeignKey(
        "core.Compound",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profile_constraints",
    )
    chemical_class = models.ForeignKey(
        "core.ChemicalClass",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profile_constraints",
    )
    formulation = models.ForeignKey(
        "core.Formulation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profile_constraints",
    )
    property_def = models.ForeignKey(
        "core.PropertyDefinition",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profile_constraints",
    )
    raw_label = models.CharField(
        max_length=256,
        blank=True,
        help_text="Original user text or a free-text fallback target.",
    )
    confidence = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    is_user_overrideable = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    reaction = models.CharField(max_length=256, blank=True)
    notes = models.TextField(blank=True)
    source = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["profile", "kind", "severity", "raw_label"]
        indexes = [
            models.Index(fields=["profile", "is_active", "kind"]),
            models.Index(fields=["compound"]),
            models.Index(fields=["chemical_class"]),
            models.Index(fields=["formulation"]),
            models.Index(fields=["property_def"]),
        ]

    def clean(self) -> None:
        normalized_targets = [
            self.compound_id,
            self.chemical_class_id,
            self.formulation_id,
            self.property_def_id,
        ]
        if sum(bool(target) for target in normalized_targets) > 1:
            raise ValidationError(
                "Set only one normalized target: compound, chemical_class, "
                "formulation, or property_def."
            )
        if not any(normalized_targets) and not self.raw_label.strip():
            raise ValidationError(
                "A profile constraint needs a normalized target or raw_label."
            )

    @property
    def target_type(self) -> str:
        if self.compound_id:
            return "compound"
        if self.chemical_class_id:
            return "chemical_class"
        if self.formulation_id:
            return "formulation"
        if self.property_def_id:
            return "property"
        return "text"

    def display_target(self) -> str:
        target = (
            self.compound
            or self.chemical_class
            or self.formulation
            or self.property_def
        )
        if target is not None:
            return str(target)
        return self.raw_label

    def __str__(self) -> str:
        return f"{self.profile}: {self.kind} {self.display_target()}"
