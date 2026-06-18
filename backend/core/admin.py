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
    DailyCheckIn,
    DailyProductUse,
    Formulation,
    FormulationIngredient,
    GlossaryTerm,
    InteractionAssertion,
    InteractionRule,
    LiteratureDiscoveryEvent,
    LiteratureReference,
    LiteratureDiscoveryTarget,
    Location,
    Profile,
    ProfileConstraint,
    ProfileLocation,
    PropertyAssertion,
    PropertyDefinition,
    ReactionEvent,
    Routine,
    RoutineItem,
    SkinProfile,
    WeatherSnapshot,
)
from core.models.brand import Brand
from core.models.product import Product


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
    readonly_fields = ('created_at','updated_at') 
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
        "formulation__product__name",
        "formulation__product__brand__name",
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
    readonly_fields = (
        "inherited_functional_classes_display",
        "effective_functional_classes_display",
    )
    fields = (
        "position",
        "raw_text",
        "compound",
        "parse_status",
        "inherited_functional_classes_display",
        "functional_classes_override",
        "function_override_source",
        "function_override_confidence",
        "function_override_notes",
        "effective_functional_classes_display",
        "is_key_active",
        "active_note",
    )
    ordering = ("position",)

    @admin.display(description="Inherited functional classes")
    def inherited_functional_classes_display(self, obj: FormulationIngredient) -> str:
        return ", ".join(obj.inherited_functional_classes)

    @admin.display(description="Effective functional classes")
    def effective_functional_classes_display(self, obj: FormulationIngredient) -> str:
        return ", ".join(obj.effective_functional_classes)


class ProductFormulationInline(admin.TabularInline):
    model = Formulation
    extra = 0
    fields = (
        "sku",
        "barcode",
        "market",
        "made_in",
        "version_label",
        "enrichment_status",
        "source",
    )


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "display_name", "website_url", "updated_at")
    search_fields = ("name", "display_name", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "brand",
        "name",
        "display_name",
        "category",
        "source",
        "updated_at",
    )
    list_filter = ("category", "source", "created_at", "updated_at")
    search_fields = ("brand__name", "name", "display_name", "category", "source_ref")
    readonly_fields = ("created_at", "updated_at")
    inlines = [ProductFormulationInline]


@admin.register(Formulation)
class FormulationAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "market",
        "made_in",
        "version_label",
        "barcode",
        "enrichment_status",
    )
    search_fields = (
        "product__name",
        "product__brand__name",
        "barcode",
        "sku",
        "market",
        "made_in",
    )
    list_filter = ("enrichment_status", "market", "made_in", "source")
    readonly_fields = ("created_at", "updated_at")
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


@admin.register(LiteratureDiscoveryTarget)
class LiteratureDiscoveryTargetAdmin(admin.ModelAdmin):
    list_display = (
        "target_type",
        "search_label",
        "reason",
        "status",
        "priority",
        "attempt_count",
        "triggered_by",
        "last_run_at",
        "created_at",
    )
    list_filter = ("target_type", "status", "reason", "triggered_by")
    search_fields = (
        "search_label",
        "compound__canonical_inci",
        "formulation__product__name",
        "product__name",
        "source_ref",
        "last_error",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "last_run_at",
        "completed_at",
    )


@admin.register(LiteratureDiscoveryEvent)
class LiteratureDiscoveryEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_type",
        "target_type",
        "search_label",
        "status",
        "priority",
        "triggered_by",
        "processed_at",
        "created_at",
    )
    list_filter = ("event_type", "target_type", "status", "triggered_by")
    search_fields = (
        "search_label",
        "dedupe_key",
        "compound__canonical_inci",
        "formulation__product__name",
        "product__name",
        "source_ref",
        "last_error",
    )
    readonly_fields = ("created_at", "updated_at", "processed_at")


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


class RoutineItemInline(admin.TabularInline):
    model = RoutineItem
    extra = 0
    fields = (
        "position",
        "routine_step",
        "custom_step_label",
        "product",
        "formulation",
        "raw_product_name",
        "frequency",
        "schedule",
    )
    ordering = ("position",)


class RoutineInline(admin.TabularInline):
    model = Routine
    extra = 0
    fields = ("name", "time_of_day", "custom_time_label", "is_active", "notes")


class ProfileLocationInline(admin.TabularInline):
    model = ProfileLocation
    extra = 0
    fields = (
        "label",
        "location",
        "is_default",
        "is_active",
        "share_weather_context",
        "source",
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    fields = (
        "id",
        "user",
        "handle",
        "display_name",
        "bio",
        "pronouns",
        "avatar_url",
        "timezone",
        "locale",
        "visibility",
        "notes",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("id", "created_at", "updated_at")
    list_display = (
        "id",
        "user",
        "handle",
        "display_name",
        "bio",
        "pronouns",
        "avatar_url",
        "timezone",
        "locale",
        "visibility",
        "notes",
        "created_at",
        "updated_at",
    )
    list_filter = ("visibility", "timezone", "locale", "created_at", "updated_at")
    search_fields = ("user__username", "user__email", "handle", "display_name")
    date_hierarchy = "created_at"
    inlines = [
        SkinProfileInline,
        ProfileConstraintInline,
        ProfileLocationInline,
        RoutineInline,
    ]


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "grid_key",
        "country",
        "region",
        "city",
        "postal_code",
        "precision",
        "updated_at",
    )
    list_filter = ("country", "precision", "source", "created_at", "updated_at")
    search_fields = ("grid_key", "label", "city", "region", "postal_code")
    readonly_fields = ("grid_key", "created_at", "updated_at")


@admin.register(ProfileLocation)
class ProfileLocationAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "label",
        "location",
        "is_default",
        "is_active",
        "share_weather_context",
        "updated_at",
    )
    list_filter = ("is_default", "is_active", "share_weather_context", "source")
    search_fields = (
        "profile__user__username",
        "profile__user__email",
        "profile__handle",
        "label",
        "location__grid_key",
        "location__city",
        "location__postal_code",
    )


@admin.register(WeatherSnapshot)
class WeatherSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "location",
        "source",
        "observed_at",
        "uv_index",
        "uv_max",
        "expires_at",
    )
    list_filter = ("source", "observed_at", "expires_at", "created_at")
    search_fields = ("location__grid_key", "location__city", "location__postal_code")
    readonly_fields = ("created_at",)


@admin.register(Routine)
class RoutineAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "name",
        "time_of_day",
        "custom_time_label",
        "is_active",
        "updated_at",
    )
    list_filter = ("time_of_day", "is_active", "created_at", "updated_at")
    search_fields = ("profile__user__username", "profile__handle", "name")
    inlines = [RoutineItemInline]


@admin.register(RoutineItem)
class RoutineItemAdmin(admin.ModelAdmin):
    list_display = (
        "routine",
        "position",
        "routine_step",
        "product",
        "formulation",
        "raw_product_name",
    )
    list_filter = ("routine_step", "routine__time_of_day", "routine__is_active")
    search_fields = (
        "routine__profile__user__username",
        "routine__name",
        "product__name",
        "product__brand__name",
        "raw_product_name",
    )


class DailyProductUseInline(admin.TabularInline):
    model = DailyProductUse
    extra = 0
    fields = (
        "time_of_day",
        "routine_step",
        "routine",
        "routine_item",
        "product",
        "formulation",
        "raw_product_name",
        "notes",
    )


@admin.register(DailyCheckIn)
class DailyCheckInAdmin(admin.ModelAdmin):
    list_display = ("profile", "checkin_date", "skin_feel", "created_at")
    list_filter = ("checkin_date", "skin_feel", "created_at")
    search_fields = ("profile__user__username", "profile__handle", "skin_notes")
    inlines = [DailyProductUseInline]


@admin.register(DailyProductUse)
class DailyProductUseAdmin(admin.ModelAdmin):
    list_display = (
        "checkin",
        "time_of_day",
        "routine_step",
        "product",
        "formulation",
        "raw_product_name",
    )
    list_filter = ("time_of_day", "routine_step", "created_at")
    search_fields = (
        "checkin__profile__user__username",
        "product__name",
        "product__brand__name",
        "raw_product_name",
    )


@admin.register(ReactionEvent)
class ReactionEventAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "title",
        "severity",
        "status",
        "occurred_on",
        "product",
        "routine",
    )
    list_filter = ("severity", "status", "occurred_on", "created_at")
    search_fields = (
        "profile__user__username",
        "profile__handle",
        "title",
        "suspected_trigger",
        "product__name",
        "product__brand__name",
    )


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
        "formulation__product__name",
        "formulation__product__brand__name",
        "property_def__key",
    )
