from core.models.product import Product

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
