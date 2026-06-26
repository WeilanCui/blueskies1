from rest_framework import serializers

from skinconcerns.models import (
    ConcernAlias,
    ConcernEvidence,
    ConcernReferralTrigger,
    ConcernRule,
    ProfileConcernSource,
    SkinConcern,
    SkinProfileConcern,
)


class SkinConcernSerializer(serializers.ModelSerializer):
    group_label = serializers.SerializerMethodField()

    class Meta:
        model = SkinConcern
        fields = [
            "id",
            "slug",
            "display_name",
            "consumer_label",
            "description",
            "group",
            "group_label",
            "concern_type",
            "recommendation_policy",
            "copy_mode",
            "is_common",
            "is_active",
        ]

    def get_group_label(self, obj: SkinConcern) -> str:
        return obj.get_group_display()


class ConcernAliasSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConcernAlias
        fields = [
            "id",
            "concern",
            "alias_text",
            "alias_type",
            "is_active",
        ]


class ConcernRuleSerializer(serializers.ModelSerializer):
    target_label = serializers.CharField(read_only=True)

    class Meta:
        model = ConcernRule
        fields = [
            "id",
            "concern",
            "key",
            "label",
            "rule_kind",
            "target_type",
            "product_category",
            "chemical_class",
            "compound",
            "property_def",
            "raw_target",
            "target_label",
            "weight",
            "rationale",
            "is_active",
        ]


class ConcernEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConcernEvidence
        fields = [
            "id",
            "concern",
            "rule",
            "literature_reference",
            "key",
            "source_name",
            "source_url",
            "citation_label",
            "evidence_type",
            "notes",
            "is_active",
        ]


class ConcernReferralTriggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConcernReferralTrigger
        fields = [
            "id",
            "concern",
            "key",
            "trigger_text",
            "description",
            "severity",
            "policy_override",
            "is_active",
        ]


class SkinProfileConcernSerializer(serializers.ModelSerializer):
    concern = SkinConcernSerializer(read_only=True)

    class Meta:
        model = SkinProfileConcern
        fields = [
            "id",
            "concern",
            "source",
            "confidence",
            "raw_text",
            "is_active",
            "created_at",
            "updated_at",
        ]


class ProfileConcernSelectionSerializer(serializers.Serializer):
    concerns = serializers.ListField(
        child=serializers.CharField(max_length=256),
        required=True,
        allow_empty=True,
    )
    source = serializers.ChoiceField(
        choices=ProfileConcernSource.choices,
        default=ProfileConcernSource.USER_SELECTED,
    )

    def validate_concerns(self, value: list[str]) -> list[str]:
        cleaned = []
        seen = set()
        for item in value:
            text = item.strip()
            key = text.casefold()
            if not text or key in seen:
                continue
            seen.add(key)
            cleaned.append(text)
        return cleaned
