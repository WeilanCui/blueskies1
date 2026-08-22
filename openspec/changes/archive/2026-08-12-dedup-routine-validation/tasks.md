## 1. Refactor

- [x] 1.1 Add module-level `resolve_product_formulation(product_id, formulation_id, raw_product_name) -> (product, formulation, raw_product_name)` to `backend/core/serializers/routine.py` (place near the existing `infer_routine_step_from_product`). Body = the exact resolution/validation/raw-fallback logic currently duplicated, with identical error keys and messages.
- [x] 1.2 Replace the duplicated block in `RoutineItemSerializer.validate` with a call to the helper, preserving the existing `attrs.pop("product_id"/"formulation_id")` reads.
- [x] 1.3 Replace the duplicated block in `RoutineAddProductSerializer.validate` with a call to the helper, preserving the existing `attrs.get(...)` reads (no pop).

## 2. Tests

- [x] 2.1 Add error-path tests (in `backend/core/tests/test_routines.py`) asserting the preserved messages via both the routine-create/update flow AND the add-product flow: unknown product_id → "Product not found."; unknown formulation_id → "Formulation not found."; mismatched product/formulation → "Formulation must belong to product."; none supplied → "Routine item needs a product, formulation, or raw_product_name."
- [x] 2.2 Confirm existing happy-path tests (create/update with product+formulation, add-product create/append/idempotent) remain and pass unchanged.

## 3. Verify

- [x] 3.1 Full backend test suite passes (`pytest`) against PostgreSQL.
- [x] 3.2 `manage.py check` clean; `manage.py makemigrations --check --dry-run` reports "No changes detected".
- [x] 3.3 `openspec validate dedup-routine-validation --strict` passes.
