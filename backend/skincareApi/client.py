"""Client for the LauraAddams skincare product API.

API docs: https://github.com/LauraAddams/skincareAPI
Base URL: https://skincare-api.herokuapp.com
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from urllib.parse import urljoin

import requests
from django.conf import settings

from core.ingestion.http import HttpError, RateLimiter, request_json

logger = logging.getLogger(__name__)

_LIMITER = RateLimiter(min_interval=0.25)


@dataclass
class SkincareProduct:
    id: int
    brand: str
    name: str
    ingredient_list: list[str] = field(default_factory=list)


@dataclass
class SkincareIngredient:
    id: int
    ingredient: str


def _base_url() -> str:
    return settings.SKINCARE_API_BASE.rstrip("/") + "/"


def _url(path: str) -> str:
    return urljoin(_base_url(), path.lstrip("/"))


def _get_list(path: str, params: dict | None = None) -> list[dict]:
    data = request_json(_url(path), params=params, limiter=_LIMITER)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("results", data.get("data", []))
    return []


def _get_object(path: str) -> dict | None:
    try:
        data = request_json(_url(path), limiter=_LIMITER)
    except HttpError as exc:
        if "404" in str(exc):
            return None
        raise
    return data if isinstance(data, dict) else None


def parse_product(raw: dict) -> SkincareProduct:
    ingredients = raw.get("ingredient_list") or raw.get("ingredients") or []
    if isinstance(ingredients, str):
        ingredients = [part.strip() for part in ingredients.split(",") if part.strip()]
    return SkincareProduct(
        id=int(raw["id"]),
        brand=str(raw.get("brand", "")),
        name=str(raw.get("name", "")),
        ingredient_list=[str(item) for item in ingredients],
    )


def parse_ingredient(raw: dict) -> SkincareIngredient:
    return SkincareIngredient(
        id=int(raw["id"]),
        ingredient=str(raw.get("ingredient", "")),
    )


def list_products() -> list[SkincareProduct]:
    return [parse_product(item) for item in _get_list("products")]


def get_product(product_id: int) -> SkincareProduct | None:
    raw = _get_object(f"products/{product_id}")
    if raw is None:
        return None
    return parse_product(raw)


def search_products(
    query: str,
    *,
    limit: int = 10,
    page: int = 1,
) -> list[SkincareProduct]:
    params = {"q": query, "limit": limit, "page": page}
    return [parse_product(item) for item in _get_list("product", params=params)]


def list_ingredients() -> list[SkincareIngredient]:
    return [parse_ingredient(item) for item in _get_list("ingredients")]


def search_ingredients(
    query: str,
    *,
    limit: int = 10,
    page: int = 1,
) -> list[SkincareIngredient]:
    params = {"q": query, "limit": limit, "page": page}
    return [parse_ingredient(item) for item in _get_list("ingredient", params=params)]


def create_product(*, brand: str, name: str, ingredients: str) -> SkincareProduct:
    """Create a product. `ingredients` is a comma-separated INCI-style string."""
    _LIMITER.wait()
    response = requests.post(
        _url("products"),
        json={"brand": brand, "name": name, "ingredients": ingredients},
        timeout=20.0,
    )
    if response.status_code == 400:
        raise HttpError(f"400 Bad Request: {response.text}")
    if response.status_code == 404:
        raise HttpError("Skincare API service unavailable (404).")
    response.raise_for_status()
    raw = response.json()
    if not isinstance(raw, dict):
        raise HttpError("Unexpected response from Skincare API.")
    return parse_product(raw)
