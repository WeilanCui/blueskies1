from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.models import Location, WeatherSnapshot, WeatherSnapshotSource


class WeatherContextUnavailable(Exception):
    """Raised when a provider cannot return usable weather/UV context."""


@dataclass(frozen=True)
class UvForecast:
    uv_index: Decimal
    observed_at: datetime
    raw_payload: dict[str, Any]
    source_ref: str


def get_or_create_shared_location(
    *,
    label: str = "",
    city: str = "",
    region: str = "",
    country: str = "US",
    postal_code: str = "",
    latitude=None,
    longitude=None,
    timezone_name: str = "",
    precision: str = "unknown",
    source: str = "manual",
) -> Location:
    candidate = Location(
        label=label,
        city=city,
        region=region,
        country=country or "US",
        postal_code=postal_code,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone_name,
        precision=precision or "unknown",
        source=source or "manual",
    )
    candidate.grid_key = candidate.build_grid_key()
    candidate.full_clean(validate_unique=False)
    grid_key = candidate.build_grid_key()
    defaults = {
        "label": candidate.label,
        "city": candidate.city,
        "region": candidate.region,
        "country": candidate.country,
        "postal_code": candidate.postal_code,
        "latitude": candidate.latitude,
        "longitude": candidate.longitude,
        "timezone": candidate.timezone,
        "precision": candidate.precision,
        "source": candidate.source,
    }
    location, created = Location.objects.get_or_create(
        grid_key=grid_key,
        defaults=defaults,
    )
    if not created:
        changed_fields = []
        for field, value in defaults.items():
            current = getattr(location, field)
            if value not in {None, ""} and current in {None, ""}:
                setattr(location, field, value)
                changed_fields.append(field)
        if changed_fields:
            changed_fields.append("updated_at")
            location.save(update_fields=changed_fields)
    return location


def get_latest_fresh_snapshot(
    location: Location,
    *,
    source: str = WeatherSnapshotSource.EPA_UV,
) -> WeatherSnapshot | None:
    return (
        WeatherSnapshot.objects.filter(
            location=location,
            source=source,
            expires_at__gt=timezone.now(),
        )
        .order_by("-observed_at", "-fetched_at")
        .first()
    )


def get_or_fetch_uv_snapshot(
    location: Location,
    *,
    force: bool = False,
) -> WeatherSnapshot | None:
    if not force:
        cached = get_latest_fresh_snapshot(location)
        if cached is not None:
            return cached

    if location.country.upper() != "US" or not location.postal_code:
        return get_latest_fresh_snapshot(location)

    try:
        forecast = fetch_epa_uv_forecast_by_zip(location.postal_code)
    except WeatherContextUnavailable:
        return get_latest_fresh_snapshot(location)

    expires_at = timezone.now() + timezone.timedelta(
        minutes=settings.EPA_UV_CACHE_MINUTES,
    )
    with transaction.atomic():
        snapshot, _ = WeatherSnapshot.objects.update_or_create(
            location=location,
            source=WeatherSnapshotSource.EPA_UV,
            observed_at=forecast.observed_at,
            defaults={
                "source_ref": forecast.source_ref,
                "fetched_at": timezone.now(),
                "expires_at": expires_at,
                "uv_index": forecast.uv_index,
                "uv_max": forecast.uv_index,
                "raw_payload": forecast.raw_payload,
            },
        )
    return snapshot


def fetch_epa_uv_forecast_by_zip(postal_code: str) -> UvForecast:
    zip_code = postal_code.strip()[:10]
    if not zip_code:
        raise WeatherContextUnavailable("EPA UV lookup requires a ZIP code.")

    path = f"getEnvirofactsUVDAILY/ZIP/{zip_code}/JSON"
    url = f"{settings.EPA_UV_API_BASE.rstrip('/')}/{path}"
    try:
        response = requests.get(
            url,
            timeout=settings.EPA_UV_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise WeatherContextUnavailable("EPA UV service unavailable.") from exc

    rows = payload if isinstance(payload, list) else [payload]
    forecasts = [_forecast_from_row(row, url) for row in rows if isinstance(row, dict)]
    forecasts = [forecast for forecast in forecasts if forecast is not None]
    if not forecasts:
        raise WeatherContextUnavailable("EPA UV service returned no UV forecast.")
    return max(forecasts, key=lambda forecast: forecast.uv_index)


def _forecast_from_row(row: dict[str, Any], source_ref: str) -> UvForecast | None:
    uv_value = _first_value(
        row,
        [
            "UV_INDEX",
            "UV_VALUE",
            "UVINDEX",
            "UV",
            "UVI",
            "INDEX_VALUE",
        ],
    )
    uv_index = _decimal_or_none(uv_value)
    if uv_index is None:
        return None

    observed_at = _parse_observed_at(
        _first_value(
            row,
            [
                "DATE_TIME",
                "DATE",
                "FORECAST_DATE",
                "VALID_DATE",
                "ISSUE_DATE",
            ],
        )
    )
    return UvForecast(
        uv_index=uv_index,
        observed_at=observed_at,
        raw_payload=row,
        source_ref=source_ref,
    )


def _first_value(row: dict[str, Any], keys: list[str]) -> Any:
    normalized = {key.upper(): value for key, value in row.items()}
    for key in keys:
        value = normalized.get(key.upper())
        if value not in {None, ""}:
            return value
    return None


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in {None, ""}:
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.1"))
    except (InvalidOperation, ValueError):
        return None


def _parse_observed_at(value: Any) -> datetime:
    if value in {None, ""}:
        return timezone.now()
    text = str(value).strip()
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y %I %p",
        "%m/%d/%Y",
        "%b/%d/%Y %I %p",
        "%b/%d/%Y",
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(text.title(), fmt)
        except ValueError:
            continue
        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed
    return timezone.now()
