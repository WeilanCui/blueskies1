from django.db import transaction
from django.db.models import Max
from rest_framework import serializers

from core.models import Formulation, Routine, RoutineItem, RoutineStep, RoutineTimeOfDay
from core.models.product import Product
from core.serializers.formulation import FormulationSerializer
from core.serializers.product import ProductSummarySerializer


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
        profile,
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
