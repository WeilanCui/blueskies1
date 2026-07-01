from django.core.exceptions import ValidationError
from django.db import models

from skinconcerns.models.choices import EvidenceType


class ConcernEvidence(models.Model):
    """Source backing for a concern definition or rule."""

    concern = models.ForeignKey(
        "skinconcerns.SkinConcern",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="evidence_links",
    )
    rule = models.ForeignKey(
        "skinconcerns.ConcernRule",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="evidence_links",
    )
    literature_reference = models.ForeignKey(
        "literature.LiteratureReference",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="concern_evidence_links",
    )
    key = models.SlugField(max_length=128, unique=True)
    source_name = models.CharField(max_length=128)
    source_url = models.URLField(max_length=1024, blank=True)
    citation_label = models.CharField(max_length=256)
    evidence_type = models.CharField(
        max_length=32,
        choices=EvidenceType.choices,
        default=EvidenceType.PUBLIC_GUIDANCE,
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["source_name", "citation_label"]
        indexes = [
            models.Index(fields=["evidence_type", "is_active"]),
            models.Index(fields=["concern", "is_active"]),
        ]

    def clean(self) -> None:
        if self.concern_id is None and self.rule_id is None:
            raise ValidationError("Concern evidence must link to a concern or rule.")

    def __str__(self) -> str:
        return self.citation_label
