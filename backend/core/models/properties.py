from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import models

from core.models.metadata import SourceMetadata, SourceType

if TYPE_CHECKING:
    from django.db.models import Manager

    from core.models.profiles import ProfileConstraint

__all__ = [
    "PropertyDomain",
    "ValueType",
    "SourceType",
    "PropertyDefinition",
    "PropertyAssertion",
    "GlossaryTerm",
]


class PropertyDomain(models.TextChoices):
    COMPOUND = "compound", "Compound (ingredient)"
    CHEMICAL_CLASS = "chemical_class", "Chemical class / family"
    FORMULATION = "formulation", "Formulation / product"
    INTERACTION = "interaction", "Ingredient interaction"
    COMPUTED = "computed", "Computed descriptor"


class ValueType(models.TextChoices):
    ENUM = "enum", "Single enum value"
    LIST = "list", "List of enum values"
    FLOAT = "float", "Numeric"
    BOOL = "bool", "Boolean"
    TEXT = "text", "Free text"
    JSON = "json", "Structured JSON"


class PropertyDefinition(models.Model):
    """Controlled vocabulary: what properties exist and how agents should derive them."""

    id: int
    assertions: Manager[PropertyAssertion]
    profile_constraints: Manager[ProfileConstraint]

    key = models.SlugField(max_length=64, unique=True)
    domain = models.CharField(max_length=32, choices=PropertyDomain.choices)
    value_type = models.CharField(max_length=16, choices=ValueType.choices)
    allowed_values = models.JSONField(
        null=True,
        blank=True,
        help_text="Allowed enum/list values, when applicable.",
    )
    label = models.CharField(max_length=128)
    description = models.TextField(
        help_text="Human- and agent-readable definition using project vocabulary.",
    )
    derivation_hint = models.TextField(
        blank=True,
        help_text="Instructions for deterministic rules or agent enrichment.",
    )
    glossary_categories = models.JSONField(
        default=list,
        blank=True,
        help_text="GlossaryTerm categories that inform this property.",
    )
    is_agent_writable = models.BooleanField(
        default=True,
        help_text="If false, only tools/rules may write (e.g. logP).",
    )
    is_required_for_enrichment = models.BooleanField(
        default=False,
        help_text="Compound/formulation enrichment incomplete until set.",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["domain", "sort_order", "key"]

    def __str__(self) -> str:
        return f"{self.key} ({self.domain})"


class PropertyAssertion(SourceMetadata):
    """A single claimed property value on a compound, chemical class, or formulation.

    Provenance fields (source_type, source_ref, source_url, confidence,
    evidence_summary, asserted_by, retrieved_at) are inherited from
    :class:`SourceMetadata`.
    """

    id: int
    compound_id: int | None
    chemical_class_id: int | None
    formulation_id: int | None
    superseded_by_id: int | None
    supersedes: Manager[PropertyAssertion]

    property_def = models.ForeignKey(
        PropertyDefinition,
        on_delete=models.CASCADE,
        related_name="assertions",
    )
    compound = models.ForeignKey(
        "core.Compound",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="property_assertions",
    )
    chemical_class = models.ForeignKey(
        "core.ChemicalClass",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="property_assertions",
    )
    formulation = models.ForeignKey(
        "core.Formulation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="property_assertions",
    )

    value_text = models.CharField(max_length=512, blank=True)
    value_numeric = models.FloatField(null=True, blank=True)
    value_bool = models.BooleanField(null=True, blank=True)
    value_json = models.JSONField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    superseded_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supersedes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        indexes = [
            models.Index(fields=["compound", "property_def", "is_active"]),
            models.Index(fields=["chemical_class", "property_def", "is_active"]),
            models.Index(fields=["formulation", "property_def", "is_active"]),
        ]

    def clean(self) -> None:
        targets = sum(
            1
            for x in (self.compound_id, self.chemical_class_id, self.formulation_id)
            if x
        )
        if targets != 1:
            raise ValidationError(
                "Exactly one of compound, chemical_class, or formulation must be set."
            )

    def __str__(self) -> str:
        target = self.compound or self.chemical_class or self.formulation
        return f"{self.property_def.key}={self.display_value()} on {target}"

    def display_value(self) -> str:
        if self.value_json is not None:
            return str(self.value_json)
        if self.value_bool is not None:
            return str(self.value_bool)
        if self.value_numeric is not None:
            return str(self.value_numeric)
        return self.value_text


class GlossaryTerm(models.Model):
    """Background vocabulary for agents and reviewers — linked to property keys."""

    term = models.CharField(max_length=128, unique=True)
    slug = models.SlugField(max_length=128, unique=True)
    category = models.CharField(max_length=64)
    definition = models.TextField()
    examples = models.JSONField(default=list, blank=True)
    related_property_keys = models.JSONField(
        default=list,
        blank=True,
        help_text="PropertyDefinition.key values this term helps interpret.",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "sort_order", "term"]

    def __str__(self) -> str:
        return self.term
