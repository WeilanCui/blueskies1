from django.db import models

from core.models.metadata import SourceMetadata


class InteractionType(models.TextChoices):
    COMPATIBLE = "compatible", "Compatible"
    INCOMPATIBLE = "incompatible", "Incompatible"
    SYNERGY = "synergy", "Synergy"
    STABILITY_RISK = "stability_risk", "Stability risk"
    SENSORY_CLASH = "sensory_clash", "Sensory clash"


class RiskClass(models.TextChoices):
    PHASE_SEPARATION = "phase_separation", "Phase separation"
    OXIDATION = "oxidation", "Oxidation"
    HYDROLYSIS = "hydrolysis", "Hydrolysis"
    PH_CONFLICT = "ph_conflict", "pH conflict"
    CHELATION = "chelation", "Chelation"
    PRECIPITATION = "precipitation", "Precipitation"
    HEAT_DEGRADATION = "heat_degradation", "Heat degradation"
    LIGHT_DEGRADATION = "light_degradation", "Light degradation"


class InteractionRule(models.Model):
    """Deterministic seed rules — matched against formulations to spawn assertions."""

    key = models.SlugField(max_length=64, unique=True)
    label = models.CharField(max_length=256)
    pattern_a = models.CharField(
        max_length=128,
        help_text="functional_class, INCI substring, or property key=value.",
    )
    pattern_b = models.CharField(max_length=128, blank=True)
    vehicle_context = models.CharField(
        max_length=64,
        blank=True,
        help_text="product_format or emulsion subtype filter, if any.",
    )
    interaction_type = models.CharField(max_length=32, choices=InteractionType.choices)
    risk_class = models.CharField(max_length=32, choices=RiskClass.choices)
    severity = models.CharField(
        max_length=16,
        choices=[("low", "Low"), ("moderate", "Moderate"), ("high", "High")],
    )
    mitigation = models.TextField(blank=True)
    evidence_summary = models.TextField(blank=True)
    source_ref = models.CharField(max_length=256, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "core_interactionrule"
        ordering = ["key"]

    def __str__(self) -> str:
        return self.key


class InteractionAssertion(SourceMetadata):
    """Observed or inferred interaction in a specific formulation context.

    Provenance fields are inherited from :class:`SourceMetadata`.
    """

    formulation = models.ForeignKey(
        "core.Formulation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="interaction_assertions",
    )
    compound_a = models.ForeignKey(
        "core.Compound",
        on_delete=models.CASCADE,
        related_name="interactions_as_a",
    )
    compound_b = models.ForeignKey(
        "core.Compound",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="interactions_as_b",
    )
    rule = models.ForeignKey(
        InteractionRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assertions",
    )
    vehicle_context = models.CharField(max_length=64, blank=True)
    interaction_type = models.CharField(max_length=32, choices=InteractionType.choices)
    risk_class = models.CharField(max_length=32, choices=RiskClass.choices)
    severity = models.CharField(
        max_length=16,
        choices=[("low", "Low"), ("moderate", "Moderate"), ("high", "High")],
    )
    mitigation = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_interactionassertion"
        indexes = [
            models.Index(fields=["formulation", "is_active"]),
            models.Index(fields=["compound_a", "compound_b"]),
        ]
