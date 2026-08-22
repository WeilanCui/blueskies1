## Why

`core/models/__init__.py` lists its `from …import` blocks and `__all__` in an ad-hoc order (e.g. `contact` before `brand`, `ChemicalClass` mid-list). Alphabetizing makes the export surface scannable and gives future additions a deterministic place to go, reducing import-block churn in diffs.

## What Changes

- Reorder the `from core.models.<module> import …` blocks alphabetically by module.
- Sort the imported names within each block alphabetically.
- Sort the `__all__` list alphabetically.
- No names added or removed; no model code touched.

## Capabilities

### New Capabilities
<!-- None — cosmetic ordering of an export module. -->

### Modified Capabilities
<!-- None — the set of exported names and all behavior is unchanged. -->

## Impact

- File: `backend/core/models/__init__.py` only.
- The public import surface (`from core.models import X`) and `__all__` membership are byte-for-byte unchanged as a set; only ordering differs.
- Note: PRs #18 (split-profile-models) and #19 (literature-app-boundary) also rewrite this file; this change is expected to need a trivial rebase/merge-conflict resolution after those land.
