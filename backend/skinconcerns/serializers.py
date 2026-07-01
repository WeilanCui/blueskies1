from rest_framework import serializers

from skinconcerns.models import (
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
