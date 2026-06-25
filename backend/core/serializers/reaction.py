from rest_framework import serializers

from core.models import DailyCheckIn, Formulation, Profile, ReactionEvent, Routine, RoutineItem
from core.models.product import Product
from core.serializers.formulation import FormulationSerializer
from core.serializers.product import ProductSummarySerializer


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
