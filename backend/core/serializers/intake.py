from django.db import transaction
from rest_framework import serializers

from core.models import (
    ConstraintEnforcement,
    ConstraintSeverity,
    FitzpatrickSkinType,
    PregnancyStatus,
    Profile,
    ProfileConstraint,
    ProfileConstraintKind,
    SkinProfile,
    SkinType,
)


PRIMARY_CONCERN_SECTIONS = [
    {
        "title": "Primary concerns",
        "items": [
            {
                "value": "acne_blemishes",
                "label": "Acne blemishes: breakouts, post-acne marks",
            },
            {"value": "dehydrated_dryness", "label": "Dehydrated / dryness"},
            {"value": "enlarged_pores", "label": "Enlarged pores"},
            {"value": "dark_circles", "label": "Dark circles"},
            {"value": "sun_damage", "label": "Sun damage"},
            {
                "value": "uneven_tone_hyperpigmentation_dull_skin",
                "label": "Uneven skin tone, hyperpigmentation, dull skin",
            },
            {
                "value": "wrinkles_firmness_elasticity",
                "label": "Wrinkles / firmness / skin elasticity",
            },
            {
                "value": "sensitive_reactive_skin",
                "label": (
                    "Sensitive or reactive skin: redness, reactive skin, "
                    "sensitivity, damaged skin barrier"
                ),
            },
        ],
    }
]


class IntakeSerializer(serializers.Serializer):
    skin_types = serializers.ListField(
        child=serializers.ChoiceField(choices=SkinType.choices),
        required=False,
        default=list,
    )
    fitzpatrick_skin_type = serializers.ChoiceField(
        choices=FitzpatrickSkinType.choices,
        required=False,
        default=FitzpatrickSkinType.NOT_PROVIDED,
    )
    baseline_sensitivity = serializers.IntegerField(
        min_value=0,
        max_value=10,
        required=False,
        allow_null=True,
    )
    primary_concerns = serializers.ListField(
        child=serializers.CharField(max_length=64),
        required=False,
        default=list,
    )
    goals = serializers.ListField(
        child=serializers.CharField(max_length=128),
        required=False,
        default=list,
    )
    goals_text = serializers.CharField(required=False, allow_blank=True)
    pregnancy_status = serializers.ChoiceField(
        choices=PregnancyStatus.choices,
        required=False,
        default=PregnancyStatus.NOT_PROVIDED,
    )
    climate = serializers.CharField(required=False, allow_blank=True, max_length=64)
    routine_notes = serializers.CharField(required=False, allow_blank=True)
    sensitivities = serializers.ListField(
        child=serializers.CharField(max_length=128),
        required=False,
        default=list,
    )

    def validate_primary_concerns(self, value: list[str]) -> list[str]:
        return self._clean_unique_list(value)

    def validate_skin_types(self, value: list[str]) -> list[str]:
        return self._clean_unique_list(value)

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        skin_types = attrs.get("skin_types", [])

        if not skin_types:
            attrs["skin_types"] = [SkinType.UNKNOWN]

        return attrs

    def validate_goals(self, value: list[str]) -> list[str]:
        return self._clean_unique_list(value)

    def validate_sensitivities(self, value: list[str]) -> list[str]:
        return self._clean_unique_list(value)

    def _clean_unique_list(self, values: list[str]) -> list[str]:
        seen = set()
        cleaned = []
        for item in values:
            value = item.strip()
            if not value or value.lower() in seen:
                continue
            seen.add(value.lower())
            cleaned.append(value)
        return cleaned

    @transaction.atomic
    def save(self, **kwargs):
        user = self.context["request"].user
        profile, _ = Profile.objects.get_or_create(user=user)
        data = self.validated_data
        goals = data.get("goals", [])
        goals_text = data.get("goals_text", "").strip()
        if goals_text:
            goals = [*goals, goals_text]

        current_profiles = profile.skin_profiles.filter(is_current=True).order_by(
            "-captured_at",
            "-id",
        )
        skin_profile = current_profiles.first()
        profile.skin_profiles.filter(is_current=True).exclude(
            pk=getattr(skin_profile, "pk", None),
        ).update(is_current=False)

        skin_profile_values = {
            "label": "Initial intake",
            "is_current": True,
            "skin_types": data["skin_types"],
            "fitzpatrick_skin_type": data.get(
                "fitzpatrick_skin_type",
                FitzpatrickSkinType.NOT_PROVIDED,
            ),
            "primary_concerns": data.get("primary_concerns", []),
            "goals": goals,
            "pregnancy_status": data.get(
                "pregnancy_status",
                PregnancyStatus.NOT_PROVIDED,
            ),
            "baseline_sensitivity": data.get("baseline_sensitivity"),
            "climate": data.get("climate", "").strip(),
            "routine_notes": data.get("routine_notes", "").strip(),
        }
        if skin_profile is None:
            skin_profile = SkinProfile.objects.create(
                profile=profile,
                **skin_profile_values,
            )
        else:
            for field, value in skin_profile_values.items():
                setattr(skin_profile, field, value)
            skin_profile.save(update_fields=[*skin_profile_values.keys()])

        profile.constraints.filter(source="intake").delete()
        for sensitivity in data.get("sensitivities", []):
            ProfileConstraint.objects.create(
                profile=profile,
                kind=ProfileConstraintKind.SENSITIVITY,
                enforcement=ConstraintEnforcement.WARN,
                severity=ConstraintSeverity.MODERATE,
                raw_label=sensitivity,
                source="intake",
            )

        return skin_profile


def intake_payload(profile: Profile) -> dict:
    skin_profile = profile.skin_profiles.filter(is_current=True).first()
    constraints = profile.constraints.filter(source="intake", is_active=True)
    return {
        "profile_id": profile.id,
        "primary_concern_sections": PRIMARY_CONCERN_SECTIONS,
        "skin_profile": None
        if skin_profile is None
        else {
            "id": skin_profile.id,
            "skin_types": skin_profile.skin_types or [SkinType.UNKNOWN],
            "fitzpatrick_skin_type": skin_profile.fitzpatrick_skin_type,
            "primary_concerns": skin_profile.primary_concerns,
            "goals": skin_profile.goals,
            "pregnancy_status": skin_profile.pregnancy_status,
            "baseline_sensitivity": skin_profile.baseline_sensitivity,
            "climate": skin_profile.climate,
            "routine_notes": skin_profile.routine_notes,
            "captured_at": skin_profile.captured_at,
        },
        "sensitivities": [constraint.raw_label for constraint in constraints],
    }
