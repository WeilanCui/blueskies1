from django.db import models


class EntityType(models.TextChoices):
    SMALL_MOLECULE = "small_molecule", "Small molecule"
    POLYMER = "polymer", "Polymer"
    SILICONE = "silicone", "Silicone"
    BOTANICAL_EXTRACT = "botanical_extract", "Botanical extract"
    MINERAL = "mineral", "Mineral"
    FRAGRANCE_BLEND = "fragrance_blend", "Fragrance blend (PARFUM)"
    MIXTURE = "mixture", "Unresolved multi-component blend"
    UVCB = "uvcb", "UVCB (variable composition)"
    NANO_MATERIAL = "nanomaterial", "Nanomaterial"
    UNKNOWN = "unknown", "Unknown"


class EnrichmentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PARTIAL = "partial", "Partially enriched"
    COMPLETE = "complete", "Complete"
    NEEDS_REVIEW = "needs_review", "Needs review"


class Compound(models.Model):
    canonical_inci = models.CharField(max_length=512, unique=True)
    display_name = models.CharField(max_length=512, blank=True)
    entity_type = models.CharField(
        max_length=32,
        choices=EntityType.choices,
        default=EntityType.UNKNOWN,
    )
    primary_cas = models.CharField(max_length=64, blank=True)
    structure_resolvable = models.BooleanField(default=False)
    enrichment_status = models.CharField(
        max_length=32,
        choices=EnrichmentStatus.choices,
        default=EnrichmentStatus.PENDING,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["canonical_inci"]

    def __str__(self) -> str:
        return self.canonical_inci

    @property
    def pubchem_url(self) -> str:
        """Link to the PubChem compound page when a CID identifier is stored."""
        ident = (
            self.identifiers.filter(id_type="pubchem_cid", is_primary=True).first()
            or self.identifiers.filter(id_type="pubchem_cid").first()
        )
        if ident is None:
            return ""
        return f"https://pubchem.ncbi.nlm.nih.gov/compound/{ident.id_value}"


class CompoundAlias(models.Model):
    compound = models.ForeignKey(
        Compound,
        on_delete=models.CASCADE,
        related_name="aliases",
    )
    alias_text = models.CharField(max_length=512)
    alias_type = models.CharField(
        max_length=32,
        choices=[
            ("inci", "INCI"),
            ("trade", "Trade name"),
            ("common", "Common name"),
            ("misspelling", "Misspelling"),
        ],
    )
    source = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["alias_text", "alias_type"],
                name="unique_compound_alias",
            )
        ]

    def __str__(self) -> str:
        return self.alias_text


class CompoundIdentifier(models.Model):
    compound = models.ForeignKey(
        Compound,
        on_delete=models.CASCADE,
        related_name="identifiers",
    )
    id_type = models.CharField(max_length=32)
    id_value = models.CharField(max_length=128)
    source = models.CharField(max_length=64, blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["id_type", "id_value"],
                name="unique_compound_identifier",
            )
        ]


class CompoundStructure(models.Model):
    compound = models.OneToOneField(
        Compound,
        on_delete=models.CASCADE,
        related_name="structure",
    )
    smiles = models.TextField(blank=True)
    inchi = models.TextField(blank=True)
    inchikey = models.CharField(max_length=27, blank=True)
    molecular_formula = models.CharField(max_length=128, blank=True)
    molecular_weight = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=64, blank=True)
    match_quality = models.CharField(
        max_length=32,
        choices=[
            ("exact", "Exact match"),
            ("salt_form", "Salt form"),
            ("parent_compound", "Parent compound"),
            ("unknown", "Unknown"),
        ],
        default="unknown",
    )
