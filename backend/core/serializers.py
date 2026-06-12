from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from core.models import (
    ChemicalClass,
    ChemicalClassMembership,
    Compound,
    CompoundAlias,
    CompoundIdentifier,
    CompoundStructure,
    ContactSubmission,
    ConstraintEnforcement,
    ConstraintSeverity,
    Formulation,
    FormulationIngredient,
    FitzpatrickSkinType,
    PregnancyStatus,
    Product,
    Profile,
    ProfileConstraint,
    ProfileConstraintKind,
    PropertyAssertion,
    SkinProfile,
    SkinType,
)


User = get_user_model()


class CompoundAliasSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompoundAlias
        fields = ["alias_text", "alias_type", "source"]


class CompoundIdentifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompoundIdentifier
        fields = ["id_type", "id_value", "source", "is_primary"]


class CompoundStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompoundStructure
        fields = [
            "smiles",
            "inchi",
            "inchikey",
            "molecular_formula",
            "molecular_weight",
            "match_quality",
            "source",
        ]


class ChemicalClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChemicalClass
        fields = ["id", "name", "slug", "description", "parent"]


class ChemicalClassMembershipSerializer(serializers.ModelSerializer):
    chemical_class = ChemicalClassSerializer(read_only=True)

    class Meta:
        model = ChemicalClassMembership
        fields = [
            "chemical_class",
            "is_primary",
            "is_active",
            "confidence",
            "source_type",
            "source_ref",
            "rationale",
        ]


class PropertyAssertionSerializer(serializers.ModelSerializer):
    key = serializers.CharField(source="property_def.key", read_only=True)
    label = serializers.CharField(source="property_def.label", read_only=True)
    value = serializers.SerializerMethodField()
    inherited_from = serializers.SerializerMethodField()

    class Meta:
        model = PropertyAssertion
        fields = [
            "key",
            "label",
            "value",
            "inherited_from",
            "source_type",
            "source_name",
            "source_ref",
            "source_url",
            "confidence",
            "evidence_summary",
            "asserted_by",
            "retrieved_at",
        ]

    def get_value(self, obj: PropertyAssertion) -> str:
        return obj.display_value()

    def get_inherited_from(self, obj: PropertyAssertion) -> str:
        if obj.chemical_class_id is None:
            return ""
        return obj.chemical_class.name


class CompoundSerializer(serializers.ModelSerializer):
    structure = CompoundStructureSerializer(read_only=True)
    aliases = CompoundAliasSerializer(many=True, read_only=True)
    identifiers = CompoundIdentifierSerializer(many=True, read_only=True)
    chemical_classes = serializers.SerializerMethodField()
    properties = serializers.SerializerMethodField()
    inherited_properties = serializers.SerializerMethodField()
    effective_properties = serializers.SerializerMethodField()
    literature_count = serializers.SerializerMethodField()

    class Meta:
        model = Compound
        fields = [
            "id",
            "canonical_inci",
            "display_name",
            "entity_type",
            "primary_cas",
            "structure_resolvable",
            "enrichment_status",
            "notes",
            "structure",
            "aliases",
            "identifiers",
            "chemical_classes",
            "properties",
            "inherited_properties",
            "effective_properties",
            "literature_count",
        ]

    def get_chemical_classes(self, obj: Compound) -> list:
        memberships = [
            membership
            for membership in obj.chemical_class_memberships.all()
            if membership.is_active
        ]
        return ChemicalClassMembershipSerializer(memberships, many=True).data

    def get_properties(self, obj: Compound) -> list:
        active = [a for a in obj.property_assertions.all() if a.is_active]
        return PropertyAssertionSerializer(active, many=True).data

    def get_inherited_properties(self, obj: Compound) -> list:
        return PropertyAssertionSerializer(
            obj.inherited_property_assertions(),
            many=True,
        ).data

    def get_effective_properties(self, obj: Compound) -> list:
        return PropertyAssertionSerializer(
            obj.effective_property_assertions(),
            many=True,
        ).data

    def get_literature_count(self, obj: Compound) -> int:
        return len(obj.literature_links.all())


class FormulationSubmitSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=512)
    brand = serializers.CharField(max_length=256, required=False, allow_blank=True, default="")
    formulation = serializers.CharField()


class AuthUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)
    display_name = serializers.CharField(allow_blank=True)
    has_completed_intake = serializers.BooleanField()


def auth_user_payload(user) -> dict:
    profile, _ = Profile.objects.get_or_create(user=user)
    return {
        "id": user.id,
        "username": user.get_username(),
        "email": user.email,
        "display_name": profile.display_name,
        "has_completed_intake": profile.skin_profiles.filter(is_current=True).exists(),
    }


def _unique_username_from_email(email: str) -> str:
    base = email.split("@", 1)[0].strip().lower() or "user"
    base = "".join(char if char.isalnum() or char in "._-" else "-" for char in base)
    base = base[:24] or "user"
    candidate = base
    counter = 1
    while User.objects.filter(username=candidate).exists():
        suffix = f"-{counter}"
        candidate = f"{base[: 30 - len(suffix)]}{suffix}"
        counter += 1
    return candidate


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    display_name = serializers.CharField(required=False, allow_blank=True, max_length=128)

    def validate_email(self, value: str) -> str:
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Unable to create an account with these credentials.")
        return email

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def create(self, validated_data: dict):
        email = validated_data["email"]
        user = User.objects.create_user(
            username=_unique_username_from_email(email),
            email=email,
            password=validated_data["password"],
        )
        Profile.objects.get_or_create(
            user=user,
            defaults={"display_name": validated_data.get("display_name", "").strip()},
        )
        return user


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs: dict) -> dict:
        identifier = attrs["identifier"].strip()
        password = attrs["password"]
        username = identifier
        if "@" in identifier:
            user = User.objects.filter(email__iexact=identifier).first()
            if user is not None:
                username = user.get_username()

        user = authenticate(
            request=self.context.get("request"),
            username=username,
            password=password,
        )
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        attrs["user"] = user
        return attrs


class ContactSubmissionSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, allow_blank=False)

    class Meta:
        model = ContactSubmission
        fields = ["id", "name", "email", "feedback", "source", "created_at"]
        read_only_fields = ["id", "created_at"]
        extra_kwargs = {
            "source": {"required": False, "allow_blank": True},
        }

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name is required.")
        return value

    def validate_email(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Email is required.")
        return value

    def validate_feedback(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Feedback is required.")
        return value


class ProductSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "brand",
            "name",
            "display_name",
            "category",
            "image_url",
        ]


class FormulationIngredientSerializer(serializers.ModelSerializer):
    compound_name = serializers.SerializerMethodField()
    enrichment_status = serializers.SerializerMethodField()

    class Meta:
        model = FormulationIngredient
        fields = [
            "position",
            "raw_text",
            "parse_status",
            "compound",
            "compound_name",
            "enrichment_status",
            "is_key_active",
            "active_note",
        ]

    def get_compound_name(self, obj: FormulationIngredient) -> str:
        if obj.compound is None:
            return ""
        return obj.compound.display_name or obj.compound.canonical_inci

    def get_enrichment_status(self, obj: FormulationIngredient) -> str:
        if obj.compound is None:
            return ""
        return obj.compound.enrichment_status


class FormulationSerializer(serializers.ModelSerializer):
    product = ProductSummarySerializer(read_only=True)
    product_id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    brand = serializers.CharField(read_only=True)
    ingredients = FormulationIngredientSerializer(many=True, read_only=True)
    ingredient_count = serializers.SerializerMethodField()

    class Meta:
        model = Formulation
        fields = [
            "id",
            "product_id",
            "product",
            "name",
            "brand",
            "sku",
            "barcode",
            "market",
            "made_in",
            "version_label",
            "effective_from",
            "effective_to",
            "enrichment_status",
            "raw_inci_text",
            "ingredient_count",
            "ingredients",
            "created_at",
        ]

    def get_ingredient_count(self, obj: Formulation) -> int:
        return obj.ingredients.count()


class IntakeSerializer(serializers.Serializer):
    skin_type = serializers.ChoiceField(choices=SkinType.choices)
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
            "skin_type": data["skin_type"],
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
        "skin_profile": None
        if skin_profile is None
        else {
            "id": skin_profile.id,
            "skin_type": skin_profile.skin_type,
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
