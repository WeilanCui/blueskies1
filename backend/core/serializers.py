from decimal import Decimal

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import Max
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
    DailyCheckIn,
    DailyProductUse,
    Formulation,
    FormulationIngredient,
    FitzpatrickSkinType,
    Location,
    PregnancyStatus,
    Profile,
    ProfileConstraint,
    ProfileConstraintKind,
    ProfileLocation,
    PropertyAssertion,
    ReactionEvent,
    ReactionSeverity,
    ReactionStatus,
    Routine,
    RoutineItem,
    RoutineStep,
    RoutineTimeOfDay,
    SkinProfile,
    SkinType,
    WeatherSnapshot,
)
from core.models.product import Product
from core.services.weather import get_or_create_shared_location


User = get_user_model()


PRIMARY_CONCERN_SECTIONS = [
    {
        "title": "Primary Focus",
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


class LocationSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=Decimal("-90"),
        max_value=Decimal("90"),
        allow_null=True,
        read_only=True,
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=Decimal("-180"),
        max_value=Decimal("180"),
        allow_null=True,
        read_only=True,
    )

    class Meta:
        model = Location
        fields = [
            "id",
            "grid_key",
            "label",
            "display_name",
            "city",
            "region",
            "country",
            "postal_code",
            "latitude",
            "longitude",
            "timezone",
            "precision",
            "source",
            "source_ref",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "grid_key", "created_at", "updated_at"]


class WeatherSnapshotSerializer(serializers.ModelSerializer):
    is_fresh = serializers.BooleanField(read_only=True)
    uv_index = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        min_value=Decimal("0"),
        max_value=Decimal("20"),
        allow_null=True,
        read_only=True,
    )
    uv_max = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        min_value=Decimal("0"),
        max_value=Decimal("20"),
        allow_null=True,
        read_only=True,
    )

    class Meta:
        model = WeatherSnapshot
        fields = [
            "id",
            "location",
            "source",
            "source_ref",
            "observed_at",
            "fetched_at",
            "expires_at",
            "uv_index",
            "uv_max",
            "temperature_c",
            "humidity_percent",
            "cloud_cover_percent",
            "air_quality_index",
            "pollen_index",
            "raw_payload",
            "is_fresh",
            "created_at",
        ]
        read_only_fields = fields


class ProfileLocationSerializer(serializers.ModelSerializer):
    location = LocationSerializer(read_only=True)
    city = serializers.CharField(required=False, allow_blank=True, write_only=True)
    region = serializers.CharField(required=False, allow_blank=True, write_only=True)
    country = serializers.CharField(required=False, allow_blank=True, write_only=True)
    postal_code = serializers.CharField(required=False, allow_blank=True, write_only=True)
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
        write_only=True,
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
        write_only=True,
    )
    timezone = serializers.CharField(required=False, allow_blank=True, write_only=True)
    precision = serializers.CharField(required=False, allow_blank=True, write_only=True)

    location_write_fields = {
        "city",
        "region",
        "country",
        "postal_code",
        "latitude",
        "longitude",
        "timezone",
        "precision",
    }

    class Meta:
        model = ProfileLocation
        fields = [
            "id",
            "label",
            "is_default",
            "is_active",
            "share_weather_context",
            "source",
            "location",
            "city",
            "region",
            "country",
            "postal_code",
            "latitude",
            "longitude",
            "timezone",
            "precision",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "location", "created_at", "updated_at"]

    def validate_label(self, value: str) -> str:
        return value.strip() or "home"

    def validate_country(self, value: str) -> str:
        return (value.strip().upper() or "US")[:2]

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        location_attrs = self._location_attrs(attrs)
        has_latitude = location_attrs.get("latitude") is not None
        has_longitude = location_attrs.get("longitude") is not None
        if self.instance is None and not any(
            [
                location_attrs.get("postal_code"),
                location_attrs.get("city"),
                has_latitude and has_longitude,
            ]
        ):
            raise serializers.ValidationError(
                "Add a postal code, city, or coordinates for this location."
            )
        if has_latitude != has_longitude:
            raise serializers.ValidationError(
                "Latitude and longitude must be provided together."
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data: dict) -> ProfileLocation:
        profile = self.context["profile"]
        location = self._resolve_location(validated_data)
        if not validated_data.get("is_default") and not profile.locations.exists():
            validated_data["is_default"] = True
        if validated_data.get("is_default"):
            ProfileLocation.objects.filter(profile=profile, is_default=True).update(
                is_default=False
            )
        profile_location = ProfileLocation.objects.create(
            profile=profile,
            location=location,
            **validated_data,
        )
        self._enforce_default(profile_location)
        return profile_location

    @transaction.atomic
    def update(self, instance: ProfileLocation, validated_data: dict) -> ProfileLocation:
        if self._has_location_input(validated_data):
            instance.location = self._resolve_location(validated_data, instance.location)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        self._enforce_default(instance)
        return instance

    def _location_attrs(self, attrs: dict) -> dict:
        return {field: attrs.get(field) for field in self.location_write_fields}

    def _has_location_input(self, attrs: dict) -> bool:
        return any(field in attrs for field in self.location_write_fields)

    def _resolve_location(
        self,
        attrs: dict,
        existing_location: Location | None = None,
    ) -> Location:
        location_attrs = {}
        for field in self.location_write_fields:
            value = attrs.pop(field, None)
            if value not in {None, ""}:
                location_attrs[field] = value

        if existing_location is not None:
            for field in self.location_write_fields:
                if field not in location_attrs:
                    location_attrs[field] = getattr(existing_location, field)

        return get_or_create_shared_location(
            city=location_attrs.get("city", ""),
            region=location_attrs.get("region", ""),
            country=location_attrs.get("country", "US"),
            postal_code=location_attrs.get("postal_code", ""),
            latitude=location_attrs.get("latitude"),
            longitude=location_attrs.get("longitude"),
            timezone_name=location_attrs.get("timezone", ""),
            precision=location_attrs.get("precision", "unknown"),
            source=attrs.get("source", "manual"),
        )

    def _enforce_default(self, profile_location: ProfileLocation) -> None:
        if not profile_location.is_default:
            return
        ProfileLocation.objects.filter(
            profile=profile_location.profile,
            is_default=True,
        ).exclude(pk=profile_location.pk).update(is_default=False)


class ProductSummarySerializer(serializers.ModelSerializer):
    brand = serializers.SerializerMethodField()

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

    def get_brand(self, obj: Product) -> str:
        if obj.brand_id is None:
            return ""
        return obj.brand.name


class FormulationIngredientSerializer(serializers.ModelSerializer):
    compound_name = serializers.SerializerMethodField()
    enrichment_status = serializers.SerializerMethodField()
    inherited_functional_classes = serializers.SerializerMethodField()
    effective_functional_classes = serializers.SerializerMethodField()
    is_function_override = serializers.SerializerMethodField()

    class Meta:
        model = FormulationIngredient
        fields = [
            "position",
            "raw_text",
            "parse_status",
            "compound",
            "compound_name",
            "enrichment_status",
            "inherited_functional_classes",
            "functional_classes_override",
            "effective_functional_classes",
            "is_function_override",
            "function_override_source",
            "function_override_confidence",
            "function_override_notes",
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

    def get_inherited_functional_classes(self, obj: FormulationIngredient) -> list[str]:
        return obj.inherited_functional_classes

    def get_effective_functional_classes(self, obj: FormulationIngredient) -> list[str]:
        return obj.effective_functional_classes

    def get_is_function_override(self, obj: FormulationIngredient) -> bool:
        return obj.is_function_override


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


class RoutineItemSerializer(serializers.ModelSerializer):
    product = ProductSummarySerializer(read_only=True)
    formulation = FormulationSerializer(read_only=True)
    product_id = serializers.IntegerField(required=False, allow_null=True)
    formulation_id = serializers.IntegerField(required=False, allow_null=True)
    display_name = serializers.CharField(read_only=True)
    id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = RoutineItem
        fields = [
            "id",
            "position",
            "routine_step",
            "custom_step_label",
            "product",
            "product_id",
            "formulation",
            "formulation_id",
            "raw_product_name",
            "display_name",
            "usage_notes",
            "frequency",
            "schedule",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        product_id = attrs.pop("product_id", None)
        formulation_id = attrs.pop("formulation_id", None)
        product = None
        formulation = None

        if product_id is not None:
            product = Product.objects.filter(pk=product_id).first()
            if product is None:
                raise serializers.ValidationError({"product_id": "Product not found."})

        if formulation_id is not None:
            formulation = Formulation.objects.select_related("product").filter(
                pk=formulation_id,
            ).first()
            if formulation is None:
                raise serializers.ValidationError(
                    {"formulation_id": "Formulation not found."}
                )
            if product is not None and formulation.product_id != product.id:
                raise serializers.ValidationError(
                    {"formulation_id": "Formulation must belong to product."}
                )
            product = product or formulation.product

        raw_product_name = attrs.get("raw_product_name", "").strip()
        if product is None and formulation is None and not raw_product_name:
            raise serializers.ValidationError(
                "Routine item needs a product, formulation, or raw_product_name."
            )

        attrs["product"] = product
        attrs["formulation"] = formulation
        attrs["raw_product_name"] = raw_product_name
        attrs["custom_step_label"] = attrs.get("custom_step_label", "").strip()
        attrs["usage_notes"] = attrs.get("usage_notes", "").strip()
        attrs["frequency"] = attrs.get("frequency", "").strip()
        attrs["schedule"] = attrs.get("schedule", "").strip()

        item_id = attrs.get("id")
        routine = self.context.get("routine_instance")
        if item_id is not None and routine is not None:
            if not routine.items.filter(pk=item_id).exists():
                raise serializers.ValidationError({"id": "Routine item not found."})

        return attrs


class RoutineSerializer(serializers.ModelSerializer):
    items = RoutineItemSerializer(many=True, required=False)

    class Meta:
        model = Routine
        fields = [
            "id",
            "name",
            "time_of_day",
            "custom_time_label",
            "is_active",
            "notes",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Routine name is required.")
        return value

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        time_of_day = attrs.get(
            "time_of_day",
            getattr(self.instance, "time_of_day", RoutineTimeOfDay.ANY),
        )
        custom_time_label = attrs.get(
            "custom_time_label",
            getattr(self.instance, "custom_time_label", ""),
        ).strip()
        if time_of_day == RoutineTimeOfDay.CUSTOM and not custom_time_label:
            raise serializers.ValidationError(
                {"custom_time_label": "Custom routines need a label."}
            )
        attrs["custom_time_label"] = custom_time_label
        attrs["notes"] = attrs.get("notes", "").strip()
        if self.instance is not None:
            self.context["routine_instance"] = self.instance
        return attrs

    @transaction.atomic
    def create(self, validated_data: dict) -> Routine:
        items = validated_data.pop("items", [])
        profile = self.context["profile"]
        routine = Routine.objects.create(profile=profile, **validated_data)
        self._replace_items(routine, items)
        self._deactivate_competing(routine)
        return routine

    @transaction.atomic
    def update(self, instance: Routine, validated_data: dict) -> Routine:
        items = validated_data.pop("items", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if items is not None:
            self._sync_items(instance, items)
        self._deactivate_competing(instance)
        return instance

    def _replace_items(self, routine: Routine, items: list[dict]) -> None:
        for index, item in enumerate(items, start=1):
            item = {**item}
            item.pop("id", None)
            item.setdefault("position", index)
            RoutineItem.objects.create(routine=routine, **item)

    def _sync_items(self, routine: Routine, items: list[dict]) -> None:
        """Update routine items in place so reordering preserves item IDs."""
        kept_ids: list[int] = []

        for offset, existing in enumerate(routine.items.all(), start=1):
            existing.position = 10_000 + offset
            existing.save(update_fields=["position"])

        for index, item_data in enumerate(items, start=1):
            item_data = {**item_data}
            position = item_data.pop("position", index)
            item_id = item_data.pop("id", None)

            if item_id is not None:
                try:
                    routine_item = routine.items.get(pk=item_id)
                except RoutineItem.DoesNotExist:
                    routine_item = None
            else:
                routine_item = None

            if routine_item is not None:
                for field, value in item_data.items():
                    setattr(routine_item, field, value)
                routine_item.position = position
                routine_item.save()
                kept_ids.append(routine_item.id)
                continue

            created = RoutineItem.objects.create(
                routine=routine,
                position=position,
                **item_data,
            )
            kept_ids.append(created.id)

        routine.items.exclude(pk__in=kept_ids).delete()

    def _deactivate_competing(self, routine: Routine) -> None:
        if not routine.is_active:
            return
        Routine.objects.filter(
            profile=routine.profile,
            time_of_day=routine.time_of_day,
            is_active=True,
        ).exclude(pk=routine.pk).update(is_active=False)


def infer_routine_step_from_product(product: Product | None) -> str:
    if product is None:
        return RoutineStep.OTHER
    category = product.category.lower()
    if "cleanser" in category or "cleanse" in category:
        return RoutineStep.CLEANSER
    if "toner" in category or "essence" in category:
        return RoutineStep.TONER_ESSENCE
    if "moistur" in category or "cream" in category:
        return RoutineStep.MOISTURIZER
    if "spf" in category or "sunscreen" in category:
        return RoutineStep.SPF
    if "mask" in category:
        return RoutineStep.MASK
    if "exfol" in category:
        return RoutineStep.EXFOLIANT
    if "eye" in category:
        return RoutineStep.EYE_CARE
    return RoutineStep.TREATMENT


class RoutineAddProductSerializer(serializers.Serializer):
    routine_id = serializers.IntegerField(required=False, allow_null=True)
    time_of_day = serializers.ChoiceField(
        choices=RoutineTimeOfDay.choices,
        required=False,
        default=RoutineTimeOfDay.AM,
    )
    custom_time_label = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=128,
    )
    routine_step = serializers.ChoiceField(
        choices=RoutineStep.choices,
        required=False,
        allow_blank=True,
    )
    product_id = serializers.IntegerField(required=False, allow_null=True)
    formulation_id = serializers.IntegerField(required=False, allow_null=True)
    raw_product_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=512,
    )
    usage_notes = serializers.CharField(required=False, allow_blank=True)
    frequency = serializers.CharField(required=False, allow_blank=True, max_length=128)
    schedule = serializers.CharField(required=False, allow_blank=True, max_length=128)

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        profile = self.context["profile"]
        routine_id = attrs.get("routine_id")
        routine = None

        if routine_id is not None:
            routine = Routine.objects.filter(profile=profile, pk=routine_id).first()
            if routine is None:
                raise serializers.ValidationError({"routine_id": "Routine not found."})

        product_id = attrs.get("product_id")
        formulation_id = attrs.get("formulation_id")
        product = None
        formulation = None

        if product_id is not None:
            product = Product.objects.filter(pk=product_id).first()
            if product is None:
                raise serializers.ValidationError({"product_id": "Product not found."})

        if formulation_id is not None:
            formulation = Formulation.objects.select_related("product").filter(
                pk=formulation_id,
            ).first()
            if formulation is None:
                raise serializers.ValidationError(
                    {"formulation_id": "Formulation not found."}
                )
            if product is not None and formulation.product_id != product.id:
                raise serializers.ValidationError(
                    {"formulation_id": "Formulation must belong to product."}
                )
            product = product or formulation.product

        raw_product_name = attrs.get("raw_product_name", "").strip()
        if product is None and formulation is None and not raw_product_name:
            raise serializers.ValidationError(
                "Routine item needs a product, formulation, or raw_product_name."
            )

        time_of_day = attrs.get("time_of_day") or RoutineTimeOfDay.AM
        custom_time_label = attrs.get("custom_time_label", "").strip()
        if routine is not None:
            time_of_day = routine.time_of_day
            custom_time_label = routine.custom_time_label
        elif time_of_day == RoutineTimeOfDay.CUSTOM and not custom_time_label:
            raise serializers.ValidationError(
                {"custom_time_label": "Custom routines need a label."}
            )

        routine_step = attrs.get("routine_step") or infer_routine_step_from_product(
            product
        )
        attrs["routine"] = routine
        attrs["time_of_day"] = time_of_day
        attrs["custom_time_label"] = custom_time_label
        attrs["routine_step"] = routine_step
        attrs["product"] = product
        attrs["formulation"] = formulation
        attrs["raw_product_name"] = raw_product_name
        attrs["usage_notes"] = attrs.get("usage_notes", "").strip()
        attrs["frequency"] = attrs.get("frequency", "").strip()
        attrs["schedule"] = attrs.get("schedule", "").strip()
        return attrs

    @transaction.atomic
    def save(self, **kwargs) -> Routine:
        profile = self.context["profile"]
        data = self.validated_data
        routine = data.get("routine") or self._get_or_create_routine(
            profile=profile,
            time_of_day=data["time_of_day"],
            custom_time_label=data["custom_time_label"],
        )

        existing_item = self._find_existing_item(
            routine=routine,
            product=data["product"],
            formulation=data["formulation"],
            raw_product_name=data["raw_product_name"],
        )
        if existing_item is not None:
            self.item = existing_item
            self.created = False
            return routine

        next_position = (
            routine.items.aggregate(max_position=Max("position"))["max_position"] or 0
        ) + 1
        self.item = RoutineItem.objects.create(
            routine=routine,
            position=next_position,
            routine_step=data["routine_step"],
            product=data["product"],
            formulation=data["formulation"],
            raw_product_name=data["raw_product_name"],
            usage_notes=data["usage_notes"],
            frequency=data["frequency"],
            schedule=data["schedule"],
        )
        self.created = True
        return routine

    def _get_or_create_routine(
        self,
        profile: Profile,
        time_of_day: str,
        custom_time_label: str,
    ) -> Routine:
        routines = Routine.objects.filter(
            profile=profile,
            time_of_day=time_of_day,
            is_active=True,
        )
        if time_of_day == RoutineTimeOfDay.CUSTOM:
            routines = routines.filter(custom_time_label__iexact=custom_time_label)
        routine = routines.order_by("id").first()
        if routine is not None:
            return routine

        if time_of_day == RoutineTimeOfDay.AM:
            name = "AM Routine"
        elif time_of_day == RoutineTimeOfDay.PM:
            name = "PM Routine"
        elif time_of_day == RoutineTimeOfDay.CUSTOM:
            name = custom_time_label
        else:
            name = "Routine"
        return Routine.objects.create(
            profile=profile,
            name=name,
            time_of_day=time_of_day,
            custom_time_label=(
                custom_time_label if time_of_day == RoutineTimeOfDay.CUSTOM else ""
            ),
            is_active=True,
        )

    def _find_existing_item(
        self,
        routine: Routine,
        product: Product | None,
        formulation: Formulation | None,
        raw_product_name: str,
    ) -> RoutineItem | None:
        if formulation is not None:
            return (
                routine.items.filter(formulation=formulation)
                .order_by("position", "id")
                .first()
            )
        if product is not None:
            return (
                routine.items.filter(product=product)
                .order_by("position", "id")
                .first()
            )
        if raw_product_name:
            return (
                routine.items.filter(raw_product_name__iexact=raw_product_name)
                .order_by("position", "id")
                .first()
            )
        return None


class DailyProductUseSerializer(serializers.ModelSerializer):
    product = ProductSummarySerializer(read_only=True)
    formulation = FormulationSerializer(read_only=True)
    routine_item = RoutineItemSerializer(read_only=True)

    class Meta:
        model = DailyProductUse
        fields = [
            "id",
            "routine",
            "routine_item",
            "product",
            "formulation",
            "raw_product_name",
            "time_of_day",
            "routine_step",
            "notes",
            "created_at",
        ]


class DailyCheckInSerializer(serializers.ModelSerializer):
    product_uses = DailyProductUseSerializer(many=True, read_only=True)
    completed_routine_item_ids = serializers.SerializerMethodField()

    class Meta:
        model = DailyCheckIn
        fields = [
            "id",
            "checkin_date",
            "skin_feel",
            "skin_notes",
            "symptoms",
            "suspected_triggers",
            "am_routine_completed",
            "pm_routine_completed",
            "product_uses",
            "completed_routine_item_ids",
            "created_at",
            "updated_at",
        ]

    def get_completed_routine_item_ids(self, obj: DailyCheckIn) -> list[int]:
        return [
            product_use.routine_item_id
            for product_use in obj.product_uses.all()
            if product_use.routine_item_id is not None
        ]


class TodayCheckInSerializer(serializers.Serializer):
    skin_feel = serializers.CharField(required=False, allow_blank=True, max_length=64)
    skin_notes = serializers.CharField(required=False, allow_blank=True)
    symptoms = serializers.ListField(
        child=serializers.CharField(max_length=128),
        required=False,
        default=list,
    )
    suspected_triggers = serializers.ListField(
        child=serializers.CharField(max_length=128),
        required=False,
        default=list,
    )
    completed_routine_item_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )

    def validate_completed_routine_item_ids(self, value: list[int]) -> list[int]:
        profile = self.context["profile"]
        item_ids = list(dict.fromkeys(value))
        existing_ids = set(
            RoutineItem.objects.filter(
                routine__profile=profile,
                pk__in=item_ids,
            ).values_list("id", flat=True)
        )
        missing_ids = [item_id for item_id in item_ids if item_id not in existing_ids]
        if missing_ids:
            raise serializers.ValidationError(
                f"Routine items not found: {', '.join(str(item_id) for item_id in missing_ids)}"
            )
        return item_ids

    @transaction.atomic
    def save(self, **kwargs) -> DailyCheckIn:
        profile = self.context["profile"]
        checkin_date = self.context["checkin_date"]
        data = self.validated_data
        checkin, _ = DailyCheckIn.objects.get_or_create(
            profile=profile,
            checkin_date=checkin_date,
            defaults={
                "skin_profile": profile.skin_profiles.filter(is_current=True).first(),
            },
        )
        checkin.skin_feel = data.get("skin_feel", "").strip()
        checkin.skin_notes = data.get("skin_notes", "").strip()
        checkin.symptoms = self._clean_unique_list(data.get("symptoms", []))
        checkin.suspected_triggers = self._clean_unique_list(
            data.get("suspected_triggers", [])
        )

        item_ids = data.get("completed_routine_item_ids", [])
        items = list(
            RoutineItem.objects.select_related("routine", "product", "formulation")
            .filter(routine__profile=profile, pk__in=item_ids)
            .order_by("routine__time_of_day", "position", "id")
        )
        completed_item_ids = {item.id for item in items}
        active_routines = profile.routines.filter(
            is_active=True,
            time_of_day__in=[RoutineTimeOfDay.AM, RoutineTimeOfDay.PM],
        ).prefetch_related("items")
        active_item_ids_by_time = {
            routine.time_of_day: {item.id for item in routine.items.all()}
            for routine in active_routines
        }
        am_item_ids = active_item_ids_by_time.get(RoutineTimeOfDay.AM)
        pm_item_ids = active_item_ids_by_time.get(RoutineTimeOfDay.PM)
        checkin.am_routine_completed = (
            am_item_ids.issubset(completed_item_ids) if am_item_ids else None
        )
        checkin.pm_routine_completed = (
            pm_item_ids.issubset(completed_item_ids) if pm_item_ids else None
        )
        checkin.save()

        checkin.product_uses.filter(routine_item__isnull=False).delete()
        for item in items:
            DailyProductUse.objects.create(
                checkin=checkin,
                routine=item.routine,
                routine_item=item,
                product=item.product,
                formulation=item.formulation,
                raw_product_name=item.raw_product_name,
                time_of_day=item.routine.time_of_day,
                routine_step=item.routine_step,
                notes=item.usage_notes,
            )

        return checkin

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


class ReactionEventSerializer(serializers.ModelSerializer):
    product = ProductSummarySerializer(read_only=True)
    formulation = FormulationSerializer(read_only=True)
    product_id = serializers.IntegerField(required=False, allow_null=True)
    formulation_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = ReactionEvent
        fields = [
            "id",
            "daily_checkin",
            "routine",
            "routine_item",
            "product",
            "product_id",
            "formulation",
            "formulation_id",
            "title",
            "severity",
            "status",
            "occurred_on",
            "resolved_on",
            "symptoms",
            "suspected_trigger",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_title(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Reaction title is required.")
        return value

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        profile = self.context["profile"]
        self._validate_owned_fk(attrs, profile)

        has_product_id = "product_id" in attrs
        has_formulation_id = "formulation_id" in attrs
        product_id = attrs.pop("product_id", None)
        formulation_id = attrs.pop("formulation_id", None)
        product = None
        formulation = None
        if has_product_id and product_id is not None:
            product = Product.objects.filter(pk=product_id).first()
            if product is None:
                raise serializers.ValidationError({"product_id": "Product not found."})
        if has_formulation_id and formulation_id is not None:
            formulation = Formulation.objects.select_related("product").filter(
                pk=formulation_id,
            ).first()
            if formulation is None:
                raise serializers.ValidationError(
                    {"formulation_id": "Formulation not found."}
                )
            if product is not None and formulation.product_id != product.id:
                raise serializers.ValidationError(
                    {"formulation_id": "Formulation must belong to product."}
                )
            product = product or formulation.product

        if has_product_id or has_formulation_id or self.instance is None:
            attrs["product"] = product
            attrs["formulation"] = formulation
        if "suspected_trigger" in attrs or self.instance is None:
            attrs["suspected_trigger"] = attrs.get("suspected_trigger", "").strip()
        if "notes" in attrs or self.instance is None:
            attrs["notes"] = attrs.get("notes", "").strip()
        if "symptoms" in attrs or self.instance is None:
            attrs["symptoms"] = self._clean_unique_list(attrs.get("symptoms", []))
        return attrs

    def _validate_owned_fk(self, attrs: dict, profile: Profile) -> None:
        owned_checks = [
            ("daily_checkin", DailyCheckIn),
            ("routine", Routine),
            ("routine_item", RoutineItem),
        ]
        for field, model in owned_checks:
            value = attrs.get(field)
            if value is None:
                continue
            queryset = model.objects.filter(pk=value.pk)
            if field == "daily_checkin":
                queryset = queryset.filter(profile=profile)
            elif field == "routine":
                queryset = queryset.filter(profile=profile)
            else:
                queryset = queryset.filter(routine__profile=profile)
            if not queryset.exists():
                raise serializers.ValidationError({field: "Object not found."})

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


CATALOG_SOURCE_PREFIX = "seed:catalog:product:"


def catalog_slug(product: Product) -> str:
    if product.source_ref.startswith(CATALOG_SOURCE_PREFIX):
        return product.source_ref.removeprefix(CATALOG_SOURCE_PREFIX)
    return str(product.pk)


def serialize_catalog_product(product: Product) -> dict:
    formulation = product.formulations.first()
    ingredients: list[dict] = []

    if formulation is not None:
        for ingredient in formulation.ingredients.all():
            ingredients.append(
                {
                    "name": ingredient.raw_text,
                    "role": "Active" if ingredient.is_key_active else "Ingredient",
                    "note": ingredient.active_note,
                    "is_key_active": ingredient.is_key_active,
                    "parse_status": ingredient.parse_status,
                }
            )

    brand_name = product.brand.name if product.brand_id else ""

    return {
        "id": catalog_slug(product),
        "product_id": product.id,
        "formulation_id": formulation.id if formulation is not None else None,
        "brand": brand_name,
        "name": product.name,
        "display_name": product.display_name or product.name,
        "category": product.category,
        "description": product.description,
        "enrichment_status": (
            formulation.enrichment_status if formulation is not None else ""
        ),
        "ingredient_count": len(ingredients),
        "ingredients": ingredients,
    }


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
        primary_skin_type = data["skin_types"][0]

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
            "skin_type": primary_skin_type,
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
            "skin_type": skin_profile.skin_type,
            "skin_types": skin_profile.skin_types or [skin_profile.skin_type],
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
