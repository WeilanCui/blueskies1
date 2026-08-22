## Why

`RoutineItemSerializer.validate` and `RoutineAddProductSerializer.validate` (`backend/core/serializers/routine.py`) contain ~20 lines of byte-identical product/formulation resolution logic: the same `Product`/`Formulation` lookups, the same "Product not found" / "Formulation not found" / "Formulation must belong to product" errors, and the same `raw_product_name` fallback requiring at least one of product/formulation/raw name. Two copies means a future fix or message change can be applied to only one path, silently diverging the two endpoints (cubic finding on PR #23, issue #25).

## What Changes

- Extract the shared resolution into a module-level helper `resolve_product_formulation(product_id, formulation_id, raw_product_name) -> (product, formulation, raw_product_name)` in `routine.py`, alongside the existing module-level `infer_routine_step_from_product`.
- Replace the duplicated block in both `RoutineItemSerializer.validate` and `RoutineAddProductSerializer.validate` with a call to the helper.
- Behavior, error messages, and error keys are unchanged — pure DRY refactor.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities

- `routine-management`: product/formulation validation for routine items is centralized; no behavior change.

## Impact

- File: `backend/core/serializers/routine.py` (`RoutineItemSerializer.validate`, `RoutineAddProductSerializer.validate`, plus the new helper).
- Tests: add explicit coverage for the error paths the refactor must preserve ("Product not found", "Formulation not found", "Formulation must belong to product", missing-all-three). Existing happy-path tests stay green.
- Stacked on PR #27 (the race fix), which is itself stacked on PR #23. Targets the #27 branch.
