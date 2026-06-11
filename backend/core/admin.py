from django.contrib import admin

from core.models import (
    ChemicalClass,
    ChemicalClassMembership,
    Compound,
    CompoundAlias,
    CompoundIdentifier,
    CompoundLiterature,
    CompoundRelationship,
    CompoundStructure,
    ContactSubmission,
    Formulation,
    FormulationIngredient,
    GlossaryTerm,
    InteractionAssertion,
    InteractionRule,
    LiteratureReference,
    Profile,
    ProfileConstraint,
    PropertyAssertion,
    PropertyDefinition,
    SkinProfile,
)


class CompoundAliasInline(admin.TabularInline):
    model = CompoundAlias
    extra = 0


class CompoundIdentifierInline(admin.TabularInline):
    model = CompoundIdentifier
    extra = 0


class ChemicalClassMembershipInline(admin.TabularInline):
    model = ChemicalClassMembership
    extra = 0
    fields = (
        "chemical_class",
        "is_primary",
        "is_active",
        "confidence",
        "source_type",
        "rationale",
    )


class PropertyAssertionInline(admin.TabularInline):
    model = PropertyAssertion
    fk_name = "compound"
    extra = 0
    fields = (
        "property_def",
        "value_text",
        "value_numeric",
        "value_bool",
        "confidence",
        "source_type",
        "is_active",
    )


@admin.register(Compound)
class CompoundAdmin(admin.ModelAdmin):
    list_display = (
        "canonical_inci",
        "entity_type",
        "enrichment_status",
        "structure_resolvable",
    )
    search_fields = ("canonical_inci", "display_name", "primary_cas")
    list_filter = ("entity_type", "enrichment_status")
    inlines = [
        CompoundAliasInline,
        CompoundIdentifierInline,
        ChemicalClassMembershipInline,
        PropertyAssertionInline,
    ]


class ChemicalClassPropertyAssertionInline(admin.TabularInline):
    model = PropertyAssertion
    fk_name = "chemical_class"
    extra = 0
    fields = (
        "property_def",
        "value_text",
        "value_numeric",
        "value_bool",
        "value_json",
        "confidence",
        "source_type",
        "is_active",
    )


@admin.register(ChemicalClass)
class ChemicalClassAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "updated_at")
    search_fields = ("name", "slug", "description")
    list_filter = ("parent",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ChemicalClassPropertyAssertionInline]


@admin.register(ChemicalClassMembership)
class ChemicalClassMembershipAdmin(admin.ModelAdmin):
    list_display = (
        "compound",
        "chemical_class",
        "is_primary",
        "is_active",
        "confidence",
        "source_type",
    )
    list_filter = ("chemical_class", "is_primary", "is_active", "source_type")
    search_fields = ("compound__canonical_inci", "chemical_class__name", "rationale")


@admin.register(PropertyDefinition)
class PropertyDefinitionAdmin(admin.ModelAdmin):
    list_display = (
        "key",
        "domain",
        "value_type",
        "is_agent_writable",
        "is_required_for_enrichment",
        "sort_order",
    )
    list_filter = ("domain", "value_type", "is_agent_writable")
    search_fields = ("key", "label", "description")
    ordering = ("domain", "sort_order", "key")


@admin.register(PropertyAssertion)
class PropertyAssertionAdmin(admin.ModelAdmin):
    list_display = (
        "property_def",
        "compound",
        "chemical_class",
        "formulation",
        "display_value",
        "confidence",
        "source_type",
        "is_active",
    )
    list_filter = ("source_type", "is_active", "property_def__domain")
    search_fields = (
        "compound__canonical_inci",
        "chemical_class__name",
        "formulation__name",
    )


@admin.register(GlossaryTerm)
class GlossaryTermAdmin(admin.ModelAdmin):
    list_display = ("term", "category", "sort_order")
    list_filter = ("category",)
    search_fields = ("term", "definition")


@admin.register(InteractionRule)
class InteractionRuleAdmin(admin.ModelAdmin):
    list_display = ("key", "interaction_type", "risk_class", "severity", "is_active")
    list_filter = ("interaction_type", "risk_class", "severity", "is_active")
    search_fields = ("key", "label", "pattern_a", "pattern_b")


class FormulationIngredientInline(admin.TabularInline):
    model = FormulationIngredient
    extra = 0
    ordering = ("position",)


@admin.register(Formulation)
class FormulationAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "enrichment_status", "barcode")
    search_fields = ("name", "brand", "barcode")
    list_filter = ("enrichment_status",)
    inlines = [FormulationIngredientInline]


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "user", "status", "source", "created_at")
    list_filter = ("status", "source", "user", "created_at")
    readonly_fields = ("created_at", "updated_at")
    search_fields = ("name", "email", "feedback", "user__username", "user__email")


@admin.register(InteractionAssertion)
class InteractionAssertionAdmin(admin.ModelAdmin):
    list_display = (
        "compound_a",
        "compound_b",
        "interaction_type",
        "risk_class",
        "severity",
        "is_active",
    )
    list_filter = ("interaction_type", "risk_class", "severity")


class CompoundLiteratureInline(admin.TabularInline):
    model = CompoundLiterature
    fk_name = "literature"
    extra = 0
    fields = (
        "compound",
        "relevance_category",
        "role_in_paper",
        "relationship_degree",
        "confidence",
    )


@admin.register(LiteratureReference)
class LiteratureReferenceAdmin(admin.ModelAdmin):
    list_display = ("pmid", "title", "journal", "year", "source", "url", "pmcid_url")
    search_fields = ("pmid", "title", "doi", "url")
    list_filter = ("source", "year")
    inlines = [CompoundLiteratureInline]


@admin.register(CompoundLiterature)
class CompoundLiteratureAdmin(admin.ModelAdmin):
    list_display = (
        "compound",
        "literature",
        "relevance_category",
        "role_in_paper",
        "relationship_degree",
        "confidence",
        "enrichment_status",
        "source_type",
    )
    list_filter = (
        "relevance_category",
        "role_in_paper",
        "relationship_degree",
        "enrichment_status",
        "source_type",
    )
    search_fields = ("compound__canonical_inci", "literature__pmid", "source_ref")


@admin.register(CompoundRelationship)
class CompoundRelationshipAdmin(admin.ModelAdmin):
    list_display = (
        "compound_a",
        "compound_b",
        "relationship_type",
        "degree",
        "confidence",
        "source_type",
    )
    list_filter = ("relationship_type", "degree", "source_type")
    search_fields = ("compound_a__canonical_inci", "compound_b__canonical_inci")


admin.site.register(CompoundStructure)


class SkinProfileInline(admin.TabularInline):
    model = SkinProfile
    extra = 0
    fields = (
        "label",
        "is_current",
        "captured_at",
        "skin_type",
        "fitzpatrick_skin_type",
        "baseline_sensitivity",
    )


class ProfileConstraintInline(admin.TabularInline):
    model = ProfileConstraint
    extra = 0
    fields = (
        "kind",
        "enforcement",
        "severity",
        "compound",
        "chemical_class",
        "formulation",
        "property_def",
        "raw_label",
        "is_active",
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "handle", "display_name", "visibility", "updated_at")
    list_filter = ("visibility",)
    search_fields = ("user__username", "user__email", "handle", "display_name")
    inlines = [SkinProfileInline, ProfileConstraintInline]


@admin.register(SkinProfile)
class SkinProfileAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "label",
        "is_current",
        "skin_type",
        "fitzpatrick_skin_type",
        "captured_at",
    )
    list_filter = ("is_current", "skin_type", "fitzpatrick_skin_type")
    search_fields = ("profile__user__username", "profile__handle", "label")


@admin.register(ProfileConstraint)
class ProfileConstraintAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "kind",
        "enforcement",
        "severity",
        "display_target",
        "confidence",
        "is_active",
    )
    list_filter = ("kind", "enforcement", "severity", "is_active")
    search_fields = (
        "profile__user__username",
        "profile__handle",
        "raw_label",
        "compound__canonical_inci",
        "chemical_class__name",
        "formulation__name",
        "property_def__key",
    )
