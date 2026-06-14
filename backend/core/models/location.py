from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha256

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.models.profiles import Profile


LOCATION_GRID_KEY_MAX_LENGTH = 160
LOCATION_GRID_KEY_HASH_LENGTH = 12


class LocationPrecision(models.TextChoices):
    POSTAL_CODE = "postal_code", "Postal code"
    CITY = "city", "City"
    GRID = "grid", "Grid"
    EXACT = "exact", "Exact"
    UNKNOWN = "unknown", "Unknown"


class LocationSource(models.TextChoices):
    MANUAL = "manual", "Manual"
    BROWSER = "browser", "Browser"
    DEVICE = "device", "Device"
    IMPORT = "import", "Import"
    SYSTEM = "system", "System"


class WeatherSnapshotSource(models.TextChoices):
    EPA_UV = "epa_uv", "EPA UV"
    WEATHER_API = "weather_api", "Weather API"
    MANUAL = "manual", "Manual"


def _clean_part(value: str | None) -> str:
    return (value or "").strip()


def _normalize_text(value: str | None) -> str:
    return _clean_part(value).lower().replace(" ", "-")


def _quantize_coord(value: Decimal | float | str | None, places: str) -> str:
    if value in {None, ""}:
        return ""
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return ""
    return str(decimal_value.quantize(Decimal(places), rounding=ROUND_HALF_UP))


def _bounded_grid_key(value: str) -> str:
    if len(value) <= LOCATION_GRID_KEY_MAX_LENGTH:
        return value

    digest = sha256(value.encode("utf-8")).hexdigest()[:LOCATION_GRID_KEY_HASH_LENGTH]
    prefix_length = LOCATION_GRID_KEY_MAX_LENGTH - LOCATION_GRID_KEY_HASH_LENGTH - 1
    return f"{value[:prefix_length]}:{digest}"


class Location(models.Model):
    """A shared normalized place used for weather/UV cache reuse."""

    grid_key = models.CharField(max_length=LOCATION_GRID_KEY_MAX_LENGTH, unique=True)
    label = models.CharField(max_length=128, blank=True)
    city = models.CharField(max_length=128, blank=True)
    region = models.CharField(max_length=128, blank=True)
    country = models.CharField(max_length=2, default="US")
    postal_code = models.CharField(max_length=24, blank=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    timezone = models.CharField(max_length=64, blank=True)
    precision = models.CharField(
        max_length=24,
        choices=LocationPrecision.choices,
        default=LocationPrecision.UNKNOWN,
    )
    source = models.CharField(
        max_length=24,
        choices=LocationSource.choices,
        default=LocationSource.MANUAL,
    )
    source_ref = models.CharField(max_length=256, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["country", "region", "city", "postal_code", "grid_key"]
        indexes = [
            models.Index(fields=["country", "region", "city"]),
            models.Index(fields=["postal_code"]),
            models.Index(fields=["precision"]),
        ]

    def clean(self) -> None:
        if not any(
            [
                self.postal_code.strip(),
                self.city.strip(),
                self.latitude is not None and self.longitude is not None,
            ]
        ):
            raise ValidationError("Location needs a postal code, city, or coordinates.")

    def save(self, *args, **kwargs):
        self.country = (self.country or "US").strip().upper()[:2]
        self.postal_code = self.postal_code.strip()
        self.city = self.city.strip()
        self.region = self.region.strip()
        self.label = self.label.strip()
        self.grid_key = self.build_grid_key()
        self.full_clean()
        super().save(*args, **kwargs)

    def build_grid_key(self) -> str:
        country = _normalize_text(self.country or "US")
        postal_code = _normalize_text(self.postal_code)
        if postal_code:
            return f"postal:{country}:{postal_code}"

        lat = _quantize_coord(self.latitude, "0.01")
        lon = _quantize_coord(self.longitude, "0.01")
        if lat and lon:
            return f"grid:{country}:{lat}:{lon}"

        region = _normalize_text(self.region)
        city = _normalize_text(self.city)
        if city or region:
            return _bounded_grid_key(f"place:{country}:{region}:{city}")

        return f"unknown:{country}"

    @property
    def display_name(self) -> str:
        if self.label:
            return self.label
        parts = [self.city, self.region, self.postal_code]
        return ", ".join(part for part in parts if part) or self.grid_key

    def __str__(self) -> str:
        return self.display_name


class ProfileLocation(models.Model):
    """A profile-owned relationship to a shared Location."""

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="locations",
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="profile_locations",
    )
    label = models.CharField(max_length=64, default="home")
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    share_weather_context = models.BooleanField(
        default=True,
        help_text="Allows this location to use shared weather/UV cache buckets.",
    )
    source = models.CharField(
        max_length=24,
        choices=LocationSource.choices,
        default=LocationSource.MANUAL,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["profile", "-is_default", "label", "id"]
        indexes = [
            models.Index(fields=["profile", "is_active", "is_default"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["profile"],
                condition=Q(is_default=True),
                name="unique_default_profile_location",
            ),
        ]

    def save(self, *args, **kwargs):
        self.label = self.label.strip() or "home"
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.profile}: {self.label} ({self.location})"


class WeatherSnapshot(models.Model):
    """Cached weather/UV context for a shared Location."""

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="weather_snapshots",
    )
    source = models.CharField(
        max_length=32,
        choices=WeatherSnapshotSource.choices,
        default=WeatherSnapshotSource.EPA_UV,
    )
    source_ref = models.CharField(max_length=256, blank=True)
    observed_at = models.DateTimeField()
    fetched_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    uv_index = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
    )
    uv_max = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
    )
    temperature_c = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    humidity_percent = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MaxValueValidator(100)],
    )
    cloud_cover_percent = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MaxValueValidator(100)],
    )
    air_quality_index = models.PositiveSmallIntegerField(null=True, blank=True)
    pollen_index = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-observed_at", "-fetched_at"]
        indexes = [
            models.Index(fields=["location", "source", "expires_at"]),
            models.Index(fields=["source", "observed_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["location", "source", "observed_at"],
                name="unique_weather_snapshot_location_source_observed",
            ),
        ]

    @property
    def is_fresh(self) -> bool:
        return self.expires_at > timezone.now()

    def __str__(self) -> str:
        return f"{self.location} {self.source} at {self.observed_at:%Y-%m-%d %H:%M}"
