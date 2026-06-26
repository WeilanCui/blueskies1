from django.db import transaction
from rest_framework import serializers

from core.models import DailyCheckIn, DailyProductUse, RoutineItem, RoutineTimeOfDay
from core.serializers.formulation import FormulationSerializer
from core.serializers.product import ProductSummarySerializer
from core.serializers.routine import RoutineItemSerializer


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
