from django.contrib import admin

from skinconcerns.models import (
    ConcernAlias,
    ConcernEvidence,
    ConcernReferralTrigger,
    ConcernRule,
    SkinConcern,
    SkinProfileConcern,
)


class ConcernAliasInline(admin.TabularInline):
    model = ConcernAlias
    extra = 0
    fields = ("alias_text", "alias_type", "is_active")
    readonly_fields = ("normalized_alias",)


class ConcernRuleInline(admin.TabularInline):
    model = ConcernRule
    extra = 0
    fields = (
        "key",
        "label",
        "rule_kind",
        "target_type",
        "product_category",
        "chemical_class",
        "compound",
        "property_def",
        "raw_target",
        "weight",
        "is_active",
    )


class ConcernEvidenceInline(admin.TabularInline):
    model = ConcernEvidence
    extra = 0
    fields = (
        "key",
        "source_name",
        "citation_label",
        "evidence_type",
        "source_url",
        "is_active",
    )


class ConcernReferralTriggerInline(admin.TabularInline):
    model = ConcernReferralTrigger
    extra = 0
    fields = ("key", "trigger_text", "severity", "policy_override", "is_active")
    readonly_fields = ("normalized_trigger",)


@admin.register(SkinConcern)
class SkinConcernAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "group",
        "concern_type",
        "recommendation_policy",
        "copy_mode",
        "is_common",
        "is_active",
    )
    list_filter = (
        "group",
        "concern_type",
        "recommendation_policy",
        "copy_mode",
        "is_common",
        "is_active",
    )
    search_fields = ("slug", "display_name", "consumer_label", "description")
    prepopulated_fields = {"slug": ("display_name",)}
    inlines = [
        ConcernAliasInline,
        ConcernRuleInline,
        ConcernEvidenceInline,
        ConcernReferralTriggerInline,
    ]


@admin.register(ConcernAlias)
class ConcernAliasAdmin(admin.ModelAdmin):
    list_display = ("alias_text", "concern", "alias_type", "is_active")
    list_filter = ("alias_type", "is_active")
    search_fields = ("alias_text", "normalized_alias", "concern__display_name")
    readonly_fields = ("normalized_alias",)


@admin.register(ConcernRule)
class ConcernRuleAdmin(admin.ModelAdmin):
    list_display = ("key", "concern", "rule_kind", "target_type", "target_label", "weight", "is_active")
    list_filter = ("rule_kind", "target_type", "is_active")
    search_fields = ("key", "label", "rationale", "product_category", "raw_target")


@admin.register(ConcernEvidence)
class ConcernEvidenceAdmin(admin.ModelAdmin):
    list_display = ("citation_label", "source_name", "evidence_type", "concern", "rule", "is_active")
    list_filter = ("source_name", "evidence_type", "is_active")
    search_fields = ("key", "citation_label", "source_name", "source_url", "notes")


@admin.register(ConcernReferralTrigger)
class ConcernReferralTriggerAdmin(admin.ModelAdmin):
    list_display = ("trigger_text", "concern", "severity", "policy_override", "is_active")
    list_filter = ("severity", "policy_override", "is_active")
    search_fields = ("trigger_text", "normalized_trigger", "description")
    readonly_fields = ("normalized_trigger",)


@admin.register(SkinProfileConcern)
class SkinProfileConcernAdmin(admin.ModelAdmin):
    list_display = ("skin_profile", "concern", "source", "confidence", "is_active")
    list_filter = ("source", "is_active", "concern__group", "concern__concern_type")
    search_fields = (
        "skin_profile__profile__user__username",
        "skin_profile__profile__handle",
        "concern__display_name",
        "raw_text",
    )
