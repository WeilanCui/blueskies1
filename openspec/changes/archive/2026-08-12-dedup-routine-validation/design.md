## Context

The two `validate` methods resolve product/formulation identically. The only real difference is how they read the id fields from `attrs`: `RoutineItemSerializer` **pops** `product_id`/`formulation_id` (so they are not passed to the model on create), while `RoutineAddProductSerializer` **gets** them (leaving them in `attrs`; `save()` reads the resolved objects from `validated_data`). The resolution + validation + raw-name fallback that follows is identical.

## Goals / Non-Goals

**Goals:**
- One source of truth for product/formulation resolution and its error messages.
- Identical external behavior: same error keys, same error strings, same returned objects, same `raw_product_name` stripping.

**Non-Goals:**
- No change to the pop-vs-get handling of id fields (kept at each call site).
- No change to any other validation in either method (routine_id lookup, time_of_day/custom_time_label, routine_step inference, item-id ownership check, field stripping).
- Not touching the unrelated cubic findings #24 (race, already fixed in #27) / #26 (`.count()`).

## Decisions

### Module-level function, not a mixin

Add a module-level helper, matching the existing `infer_routine_step_from_product` already in this file:

```python
def resolve_product_formulation(
    product_id: int | None,
    formulation_id: int | None,
    raw_product_name: str,
) -> tuple[Product | None, Formulation | None, str]:
    product = None
    formulation = None
    if product_id is not None:
        product = Product.objects.filter(pk=product_id).first()
        if product is None:
            raise serializers.ValidationError({"product_id": "Product not found."})
    if formulation_id is not None:
        formulation = (
            Formulation.objects.select_related("product")
            .filter(pk=formulation_id)
            .first()
        )
        if formulation is None:
            raise serializers.ValidationError({"formulation_id": "Formulation not found."})
        if product is not None and formulation.product_id != product.id:
            raise serializers.ValidationError(
                {"formulation_id": "Formulation must belong to product."}
            )
        product = product or formulation.product
    raw = (raw_product_name or "").strip()
    if product is None and formulation is None and not raw:
        raise serializers.ValidationError(
            "Routine item needs a product, formulation, or raw_product_name."
        )
    return product, formulation, raw
```

A free function is simpler than a mixin (no MRO/`self` coupling) and the helper needs nothing from serializer instance state.

### Call sites

- `RoutineItemSerializer.validate`: `product_id = attrs.pop("product_id", None)`, `formulation_id = attrs.pop("formulation_id", None)`, then `product, formulation, raw_product_name = resolve_product_formulation(product_id, formulation_id, attrs.get("raw_product_name", ""))`. The pops are preserved.
- `RoutineAddProductSerializer.validate`: `product, formulation, raw_product_name = resolve_product_formulation(attrs.get("product_id"), attrs.get("formulation_id"), attrs.get("raw_product_name", ""))`. No pop (unchanged).

Everything after (assigning `attrs["product"]`, etc.) is unchanged.

## Risks / Trade-offs

- **Subtle behavior drift** during extraction (e.g. dropping a `select_related`, changing an error key). Mitigated by adding explicit error-path tests for all three error messages + the missing-all case, exercised through both serializers/endpoints.
- The `pop` vs `get` asymmetry is deliberately retained; the helper takes already-read ids so each caller keeps its own read semantics.
