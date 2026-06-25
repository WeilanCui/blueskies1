## Why

`core/serializers.py` is a single 1510-line module holding ~25 DRF serializers plus loose helper functions spanning every domain (compounds, auth, locations, formulations, routines, check-ins, reactions, catalog, intake). The monolith is hard to navigate, produces noisy diffs, and diverges from `core/models/`, which is already a per-domain package. Splitting serializers into a package mirroring `core/models/` makes the surface scannable and gives new serializers a deterministic home.

## What Changes

- Replace the `core/serializers.py` module with a `core/serializers/` package.
- Move each serializer (and its co-located helper functions) into a per-domain submodule mirroring `core/models/`: `compound`, `auth`, `contact`, `location`, `product`, `formulation`, `routine`, `daily_checkin`, `reaction`, `catalog`, `intake`.
- Add `core/serializers/__init__.py` that re-exports the full public surface (flat, alphabetized) so `from core.serializers import X` keeps working unchanged.
- No serializer behavior, fields, validation, or method bodies change — pure code-move + re-export.

## Capabilities

### New Capabilities
<!-- None — structural refactor of an existing module. -->

### Modified Capabilities
<!-- None — public import surface and all serializer behavior are unchanged. -->

## Impact

- File: `backend/core/serializers.py` → `backend/core/serializers/` package (one submodule per domain + `__init__.py`).
- Importers (`core/views.py`, `core/tests/test_formulation_ingredient_functions.py`) are unchanged: both use `from core.serializers import …`, which the re-export preserves.
- The public import surface (every name imported elsewhere) is byte-for-byte unchanged as a set; only file location differs.
