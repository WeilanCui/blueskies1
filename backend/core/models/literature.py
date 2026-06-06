from django.db import models

from core.models.metadata import SourceMetadata


class RelevanceCategory(models.TextChoices):
    SIDE_EFFECT = "side_effect", "Side effect / adverse event"
    SAFETY_PROFILE = "safety_profile", "Safety profile"
    SENSITIZATION = "sensitization", "Sensitization / contact allergy"
    IRRITATION = "irritation", "Irritation"
    EFFICACY = "efficacy", "Efficacy"
    INTERACTION = "interaction", "Ingredient interaction"
    PRESERVATION_PERFORMANCE = "preservation_performance", "Preservation performance"
    STABILITY = "stability", "Stability / shelf life"
    GENERAL = "general", "General relevance"


class RoleInPaper(models.TextChoices):
    SUBJECT = "subject", "Primary subject"
    SOLVENT = "solvent", "Solvent / vehicle"
    CO_INGREDIENT = "co_ingredient", "Co-ingredient"
    COMPARATOR = "comparator", "Comparator"
    UNKNOWN = "unknown", "Unknown"


class RelationshipType(models.TextChoices):
    CO_MENTION = "co_mention", "Co-mentioned in literature"
    SYNERGY = "synergy", "Synergy"
    ANTAGONISM = "antagonism", "Antagonism"


class LiteratureReference(models.Model):
    """A single bibliographic record (currently PubMed) used as evidence."""

    pmid = models.CharField(max_length=32, unique=True)
    title = models.TextField(blank=True)
    abstract = models.TextField(blank=True)
    journal = models.CharField(max_length=512, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    doi = models.CharField(max_length=255, blank=True)
    url = models.URLField(
        max_length=1024,
        blank=True,
        help_text="Canonical link to the reference (PubMed/DOI landing page).",
    )
    mesh_terms = models.JSONField(default=list, blank=True)
    substances = models.JSONField(default=list, blank=True)
    source = models.CharField(max_length=32, default="pubmed")
    fetched_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "pmid"]
        indexes = [models.Index(fields=["pmid"])]

    def __str__(self) -> str:
        return f"PMID {self.pmid}"


class CompoundLiterature(SourceMetadata):
    """Links a compound to a reference with how/why it is relevant.

    Provenance fields are inherited from :class:`SourceMetadata`.
    """

    compound = models.ForeignKey(
        "core.Compound",
        on_delete=models.CASCADE,
        related_name="literature_links",
    )
    literature = models.ForeignKey(
        LiteratureReference,
        on_delete=models.CASCADE,
        related_name="compound_links",
    )
    relevance_category = models.CharField(
        max_length=32,
        choices=RelevanceCategory.choices,
        default=RelevanceCategory.GENERAL,
    )
    role_in_paper = models.CharField(
        max_length=16,
        choices=RoleInPaper.choices,
        default=RoleInPaper.UNKNOWN,
    )
    relationship_degree = models.PositiveSmallIntegerField(
        default=1,
        help_text="0 = direct query subject, 1/2 = via co-mentioned compounds.",
    )
    confidence = models.FloatField(default=0.5)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["compound", "literature"],
                name="unique_compound_literature",
            )
        ]
        indexes = [
            models.Index(fields=["compound", "relevance_category"]),
            models.Index(fields=["relationship_degree"]),
        ]

    def __str__(self) -> str:
        return f"{self.compound} <- {self.literature} ({self.relevance_category})"


class CompoundRelationship(SourceMetadata):
    """A literature-derived relationship between two compounds.

    Provenance fields are inherited from :class:`SourceMetadata`.
    """

    compound_a = models.ForeignKey(
        "core.Compound",
        on_delete=models.CASCADE,
        related_name="relationships_as_a",
    )
    compound_b = models.ForeignKey(
        "core.Compound",
        on_delete=models.CASCADE,
        related_name="relationships_as_b",
    )
    relationship_type = models.CharField(
        max_length=32,
        choices=RelationshipType.choices,
        default=RelationshipType.CO_MENTION,
    )
    degree = models.PositiveSmallIntegerField(default=1)
    confidence = models.FloatField(default=0.5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["compound_a", "compound_b", "relationship_type"],
                name="unique_compound_relationship",
            )
        ]
        indexes = [models.Index(fields=["compound_a", "relationship_type"])]

    def __str__(self) -> str:
        return f"{self.compound_a} ~ {self.compound_b} ({self.relationship_type})"
