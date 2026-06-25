from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models

from core.models.metadata import SourceMetadata

if TYPE_CHECKING:
    from django.db.models import Manager

    from core.models.formulation import FormulationIngredient
    from core.models.interactions import InteractionAssertion
    from core.models.literature import CompoundLiterature, CompoundRelationship
    from core.models.profiles import ProfileConstraint
    from core.models.properties import PropertyAssertion


class ChemicalClass(models.Model):
    """A reusable chemical family whose properties can be inherited by compounds."""

    id: int
    children: Manager[ChemicalClass]
    memberships: Manager[ChemicalClassMembership]
    property_assertions: Manager[PropertyAssertion]
    profile_constraints: Manager[ProfileConstraint]

    name = models.CharField(max_length=128, unique=True)
    slug = models.SlugField(max_length=128, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


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
    id: int
    identifiers: Manager[CompoundIdentifier]
    property_assertions: Manager[PropertyAssertion]
    chemical_class_memberships: Manager[ChemicalClassMembership]
    literature_links: Manager[CompoundLiterature]
    relationships_as_a: Manager[CompoundRelationship]
    relationships_as_b: Manager[CompoundRelationship]
    interactions_as_a: Manager[InteractionAssertion]
    interactions_as_b: Manager[InteractionAssertion]
    profile_constraints: Manager[ProfileConstraint]
    formulation_appearances: Manager[FormulationIngredient]

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

    def inherited_property_assertions(self):
        """Active class properties that apply when no direct compound claim exists."""
        from core.models.properties import PropertyAssertion

        direct_property_ids = self.property_assertions.filter(
            is_active=True,
        ).values_list("property_def_id", flat=True)
        return (
            PropertyAssertion.objects.filter(
                chemical_class__memberships__compound=self,
                chemical_class__memberships__is_active=True,
                is_active=True,
            )
            .exclude(property_def_id__in=direct_property_ids)
            .select_related("property_def", "chemical_class")
            .distinct()
        )

    def effective_property_assertions(self):
        """Direct active compound properties plus inherited class properties."""
        direct = self.property_assertions.filter(
            is_active=True,
        ).select_related("property_def")
        return list(direct) + list(self.inherited_property_assertions())


class ChemicalClassMembership(SourceMetadata):
    """Links a compound to a chemical family such as Retinoids."""

    compound = models.ForeignKey(
        Compound,
        on_delete=models.CASCADE,
        related_name="chemical_class_memberships",
    )
    chemical_class = models.ForeignKey(
        ChemicalClass,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    rationale = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        ordering = ["chemical_class__name", "compound__canonical_inci"]
        constraints = [
            models.UniqueConstraint(
                fields=["compound", "chemical_class"],
                name="unique_compound_chemical_class",
            )
        ]

    def __str__(self) -> str:
        return f"{self.compound} belongs to {self.chemical_class}"


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
