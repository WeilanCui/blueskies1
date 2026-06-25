from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from core.models import Location, ProfileLocation, WeatherSnapshot
from core.services.weather import get_or_create_shared_location


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
