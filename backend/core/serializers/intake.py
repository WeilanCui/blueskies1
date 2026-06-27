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
from skinconcerns.models import ProfileConcernSource
from skinconcerns.serializers import SkinProfileConcernSerializer
from skinconcerns.services import ConcernPolicyService, ConcernSelectionService


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
    concerns = serializers.ListField(
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

    def validate_concerns(self, value: list[str]) -> list[str]:
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

        ConcernSelectionService().set_skin_profile_concerns(
            skin_profile,
            data.get("concerns", []),
            source=ProfileConcernSource.USER_SELECTED,
        )

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
    concern_service = ConcernSelectionService()
    concern_policy_service = ConcernPolicyService()
    concern_selections = (
        []
        if skin_profile is None
        else list(concern_service.active_for_skin_profile(skin_profile))
    )
    return {
        "profile_id": profile.id,
        "skin_profile": None
        if skin_profile is None
        else {
            "id": skin_profile.id,
            "skin_types": skin_profile.skin_types or [SkinType.UNKNOWN],
            "fitzpatrick_skin_type": skin_profile.fitzpatrick_skin_type,
            "concerns": SkinProfileConcernSerializer(
                concern_selections,
                many=True,
            ).data,
            "concern_policy": concern_policy_service.policy_for_concerns(
                selection.concern for selection in concern_selections
            ),
            "goals": skin_profile.goals,
            "pregnancy_status": skin_profile.pregnancy_status,
            "baseline_sensitivity": skin_profile.baseline_sensitivity,
            "climate": skin_profile.climate,
            "routine_notes": skin_profile.routine_notes,
            "captured_at": skin_profile.captured_at,
        },
        "sensitivities": [constraint.raw_label for constraint in constraints],
    }
