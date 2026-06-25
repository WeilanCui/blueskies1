from __future__ import annotations

from pathlib import Path

from django.db import transaction

from core.models import Compound, EnrichmentStatus, Formulation, FormulationIngredient
from core.models.brand import Brand
from core.models.product import Product
from core.seeds.catalog import REFERENCE_BRANDS, REFERENCE_PRODUCTS
from core.seeds.csv_catalog import iter_csv_product_rows
from literature.ingestion.formulation_ingest import resolve_compound


def _seed_source_ref(kind: str, *parts: str) -> str:
    return f"seed:catalog:{kind}:" + ":".join(parts)


def _csv_source_ref(source_file: str, line_number: int) -> str:
    stem = Path(source_file).stem
    return f"seed:csv:{stem}:L{line_number}"


def _upsert_brand(row: dict) -> tuple[Brand, bool]:
    defaults = {
        "display_name": row.get("display_name", ""),
        "description": row.get("description", ""),
        "website_url": row.get("website_url", ""),
        "image_url": row.get("image_url", ""),
    }
    brand = Brand.objects.filter(name__iexact=row["name"]).first()
    if brand is None:
        return Brand.objects.create(name=row["name"], **defaults), True

    changed = False
    for field, value in defaults.items():
        if getattr(brand, field) != value:
            setattr(brand, field, value)
            changed = True
    if changed:
        brand.save()
    return brand, False


def _resolve_ingredient_compound(row: dict) -> tuple[Compound | None, str]:
    compound_inci = row.get("compound_inci")
    if compound_inci:
        compound = Compound.objects.filter(canonical_inci=compound_inci).first()
        if compound is not None:
            return compound, "matched"

    compound, parse_status = resolve_compound(row["raw_text"])
    return compound, parse_status


def _sync_formulation_ingredients(
    formulation: Formulation,
    ingredient_rows: list[dict],
) -> int:
    formulation.ingredients.all().delete()
    written = 0

    for position, row in enumerate(ingredient_rows, start=1):
        compound, parse_status = _resolve_ingredient_compound(row)
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=position,
            raw_text=row["raw_text"],
            compound=compound,
            parse_status=parse_status,
            is_key_active=row.get("is_key_active", False),
            active_note=row.get("active_note", ""),
        )
        written += 1

    return written


@transaction.atomic
def upsert_brands() -> dict[str, int]:
    created = updated = 0
    for row in REFERENCE_BRANDS:
        _, was_created = _upsert_brand(row)
        if was_created:
            created += 1
        else:
            updated += 1
    return {"created": created, "updated": updated}


@transaction.atomic
def upsert_catalog() -> dict[str, int]:
    brands_created = brands_updated = 0
    products_created = products_updated = 0
    formulations_created = formulations_updated = 0
    ingredients_written = 0

    brand_by_key: dict[str, Brand] = {}
    for row in REFERENCE_BRANDS:
        brand, was_created = _upsert_brand(row)
        brand_by_key[row["key"]] = brand
        if was_created:
            brands_created += 1
        else:
            brands_updated += 1

    for row in REFERENCE_PRODUCTS:
        brand = brand_by_key[row["brand_key"]]
        source_ref = _seed_source_ref("product", row["key"])
        defaults = {
            "brand": brand,
            "name": row["name"],
            "display_name": row.get("display_name", ""),
            "category": row.get("category", ""),
            "description": row.get("description", ""),
            "image_url": row.get("image_url", ""),
            "source": "seed",
        }
        product = Product.objects.filter(source_ref=source_ref).first()
        if product is None:
            product = Product.objects.create(source_ref=source_ref, **defaults)
            products_created += 1
        else:
            for field, value in defaults.items():
                setattr(product, field, value)
            product.save()
            products_updated += 1

        for formulation_row in row.get("formulations", []):
            formulation_ref = _seed_source_ref(
                "formulation",
                row["key"],
                formulation_row["key"],
            )
            formulation_defaults = {
                "product": product,
                "raw_inci_text": formulation_row.get("raw_inci_text", ""),
                "market": formulation_row.get("market", ""),
                "made_in": formulation_row.get("made_in", ""),
                "version_label": formulation_row.get("version_label", ""),
                "barcode": formulation_row.get("barcode"),
                "source": "seed",
                "enrichment_status": EnrichmentStatus.PENDING,
            }
            formulation = Formulation.objects.filter(source_ref=formulation_ref).first()
            if formulation is None:
                formulation = Formulation.objects.create(
                    source_ref=formulation_ref,
                    **formulation_defaults,
                )
                formulations_created += 1
            else:
                for field, value in formulation_defaults.items():
                    setattr(formulation, field, value)
                formulation.save()
                formulations_updated += 1

            ingredients_written += _sync_formulation_ingredients(
                formulation,
                formulation_row.get("ingredients", []),
            )

    return {
        "brands_created": brands_created,
        "brands_updated": brands_updated,
        "products_created": products_created,
        "products_updated": products_updated,
        "formulations_created": formulations_created,
        "formulations_updated": formulations_updated,
        "ingredients_written": ingredients_written,
    }


@transaction.atomic
def upsert_csv_catalog(*, seed_dir=None) -> dict[str, int]:
    brands_created = brands_updated = 0
    products_created = products_updated = 0
    formulations_created = formulations_updated = 0
    ingredients_written = 0
    files_processed = 0
    rows_skipped = 0

    seen_files: set[str] = set()
    brand_cache: dict[str, Brand] = {}

    for row in iter_csv_product_rows(seed_dir):
        seen_files.add(row["source_file"])

        brand_name = row["brand"]
        brand = brand_cache.get(brand_name.lower())
        if brand is None:
            brand, was_created = _upsert_brand({"name": brand_name})
            brand_cache[brand_name.lower()] = brand
            if was_created:
                brands_created += 1
            else:
                brands_updated += 1

        source_ref = _csv_source_ref(row["source_file"], row["line_number"])
        product_defaults = {
            "brand": brand,
            "name": row["product_name"],
            "display_name": row["product_name"],
            "source": "seed_csv",
        }
        product = Product.objects.filter(source_ref=source_ref).first()
        if product is None:
            product = (
                Product.objects.filter(
                    brand=brand,
                    name__iexact=row["product_name"],
                )
                .order_by("id")
                .first()
            )
        if product is None:
            product = Product.objects.create(source_ref=source_ref, **product_defaults)
            products_created += 1
        else:
            for field, value in product_defaults.items():
                setattr(product, field, value)
            if not product.source_ref:
                product.source_ref = source_ref
            product.save()
            products_updated += 1

        formulation_ref = f"{source_ref}:formulation"
        formulation_defaults = {
            "product": product,
            "raw_inci_text": row["raw_inci_text"],
            "source": "seed_csv",
            "enrichment_status": EnrichmentStatus.PENDING,
            "version_label": "CSV import",
        }
        formulation = Formulation.objects.filter(source_ref=formulation_ref).first()
        if formulation is None:
            formulation = Formulation.objects.create(
                source_ref=formulation_ref,
                **formulation_defaults,
            )
            formulations_created += 1
        else:
            for field, value in formulation_defaults.items():
                setattr(formulation, field, value)
            formulation.save()
            formulations_updated += 1

        ingredient_rows = [{"raw_text": text} for text in row["ingredients"]]
        if not ingredient_rows:
            rows_skipped += 1
            continue

        ingredients_written += _sync_formulation_ingredients(
            formulation,
            ingredient_rows,
        )

    files_processed = len(seen_files)
    return {
        "files_processed": files_processed,
        "brands_created": brands_created,
        "brands_updated": brands_updated,
        "products_created": products_created,
        "products_updated": products_updated,
        "formulations_created": formulations_created,
        "formulations_updated": formulations_updated,
        "ingredients_written": ingredients_written,
        "rows_skipped": rows_skipped,
    }


def seed_catalog(
    *,
    include_reference: bool = True,
    include_csv: bool = True,
    seed_dir=None,
) -> dict[str, dict[str, int]]:
    results: dict[str, dict[str, int]] = {}
    if include_reference:
        results["reference"] = upsert_catalog()
    if include_csv:
        results["csv"] = upsert_csv_catalog(seed_dir=seed_dir)
    return results
