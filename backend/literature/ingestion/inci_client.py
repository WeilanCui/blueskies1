"""INCI API client: search + ingredient detail from inciapi.com."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from urllib.parse import quote

from django.conf import settings

from literature.ingestion.http import HttpError, RateLimiter, request_json

logger = logging.getLogger(__name__)

_LIMITER = RateLimiter(min_interval=0.2)

# Future: get_product(barcode) -> InciProduct; analyze(inci_list) -> analysis payload.


@dataclass
class InciIngredient:
    inci_name: str
    aliases: list[str] = field(default_factory=list)
    cas_number: str = ""
    ec_number: str = ""
    description: str = ""
    functions: list[str] = field(default_factory=list)
    safety_score: float | None = None
    safety_level: str = ""
    is_eu_allergen: bool = False
    allergen_types: list[str] = field(default_factory=list)
    comedogenicity_rating: int | None = None
    irritancy_potential: str = ""
    suitable_for_skin_types: list[str] = field(default_factory=list)
    avoid_for_skin_types: list[str] = field(default_factory=list)
    pregnancy_safe: str = ""
    eu_status: str = ""
    regulations: list[str] = field(default_factory=list)
    photosensitivity_risk: str = ""
    stability: str = ""
    optimal_ph_range: str = ""
    evidence_quality: int | None = None
    raw: dict = field(default_factory=dict)


def _headers() -> dict[str, str]:
    api_key = settings.INCI_API_KEY
    if not api_key:
        raise HttpError(
            "INCI_API_KEY is not configured. Set it in .env to use the INCI API."
        )
    return {"X-API-Key": api_key}


def _get(path: str, params: dict | None = None) -> dict:
    base = settings.INCI_API_BASE.rstrip("/")
    url = f"{base}{path}"
    return request_json(url, params=params, headers=_headers(), limiter=_LIMITER)


def search_ingredients(query: str, limit: int = 10) -> list[InciIngredient]:
    """Search ingredients by name; returns parsed result rows."""
    data = _get("/ingredients/search", params={"q": query, "limit": limit})
    return [parse_ingredient(item) for item in data.get("results", [])]


def get_ingredient(inci_name: str) -> InciIngredient | None:
    """Fetch a single ingredient by INCI name. None if not found."""
    quoted = quote(inci_name, safe="")
    try:
        data = _get(f"/ingredients/{quoted}")
    except HttpError as exc:
        if "404" in str(exc):
            logger.info("INCI ingredient not found: %r", inci_name)
            return None
        raise
    ingredient = data.get("ingredient")
    if not ingredient:
        return None
    return parse_ingredient(ingredient)


def parse_ingredient(data: dict) -> InciIngredient:
    """Map a raw INCI API ingredient dict to a typed record."""
    return InciIngredient(
        inci_name=data.get("inciName", "") or "",
        aliases=list(data.get("aliases") or []),
        cas_number=data.get("casNumber", "") or "",
        ec_number=data.get("ecNumber", "") or "",
        description=data.get("description", "") or "",
        functions=list(data.get("functions") or []),
        safety_score=_to_float(data.get("safetyScore")),
        safety_level=data.get("safetyLevel", "") or "",
        is_eu_allergen=bool(data.get("isEuAllergen")),
        allergen_types=list(data.get("allergenTypes") or []),
        comedogenicity_rating=_to_int(data.get("comedogenicityRating")),
        irritancy_potential=data.get("irritancyPotential", "") or "",
        suitable_for_skin_types=list(data.get("suitableForSkinTypes") or []),
        avoid_for_skin_types=list(data.get("avoidForSkinTypes") or []),
        pregnancy_safe=data.get("pregnancySafe", "") or "",
        eu_status=data.get("euStatus", "") or "",
        regulations=list(data.get("regulations") or []),
        photosensitivity_risk=data.get("photosensitivityRisk", "") or "",
        stability=data.get("stability", "") or "",
        optimal_ph_range=data.get("optimalPhRange", "") or "",
        evidence_quality=_to_int(data.get("evidenceQuality")),
        raw=data,
    )


def _to_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
