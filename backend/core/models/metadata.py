from django.db import models


class SourceType(models.TextChoices):
    COMPUTED = "computed", "Computed (RDKit, rules)"
    REGULATORY = "regulatory", "Regulatory (CosIng, CIR)"
    LITERATURE = "literature", "Literature / RAG"
    AGGREGATOR = "aggregator", "Third-party aggregator (INCI API)"
    AGENT = "agent", "Agent inference"
    HUMAN = "human", "Human review"
    SEED = "seed", "Reference seed data"


class SourceMetadata(models.Model):
    """Abstract provenance mixin.

    Captures *where* a piece of data came from, *how* trustworthy it is, and
    *when* it was gathered. Any model whose rows represent a sourced claim
    (assertions, literature links, relationships) should inherit from this so
    provenance is recorded uniformly and references are linkable.
    """

    source_type = models.CharField(
        max_length=32,
        choices=SourceType.choices,
        blank=True,
        help_text="Kind of source (computed, regulatory, literature, agent, etc.).",
    )
    source_name = models.CharField(
        max_length=128,
        blank=True,
        help_text="Originating database, registry, or publisher (e.g. PubChem, CosIng, PubMed).",
    )
    source_ref = models.CharField(
        max_length=512,
        blank=True,
        help_text="Stable identifier or citation within the source (CID, PMID, accession, DOI).",
    )
    source_url = models.URLField(
        max_length=1024,
        blank=True,
        help_text="Direct link to the referenced record or document.",
    )
    confidence = models.FloatField(
        default=1.0,
        help_text="0-1 confidence in this claim given its source.",
    )
    evidence_summary = models.TextField(
        blank=True,
        help_text="Short human-readable justification or quote supporting the claim.",
    )
    asserted_by = models.CharField(
        max_length=128,
        blank=True,
        help_text="Agent, tool, or person that produced this record.",
    )
    retrieved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the source information was gathered/fetched.",
    )

    class Meta:
        abstract = True
