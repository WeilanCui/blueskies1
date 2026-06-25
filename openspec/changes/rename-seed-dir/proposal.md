## Why

The repo has three things named "seed": `backend/seed/` (raw CSV data), `backend/core/seeds/` (Python loaders), and `backend/literature/seeds/` (ontology seeds). The collision makes it ambiguous which "seed" a path or import refers to. Renaming the raw-data directory to `backend/data/` removes the clash and makes its role (input data, not code) obvious.

## What Changes

- Rename `backend/seed/` → `backend/data/` (via `git mv`, preserving the 5 CSVs' history).
- Update the one code path constant that points at it: `DEFAULT_SEED_DIR` in `core/seeds/csv_catalog.py` (`"seed"` → `"data"`).
- Update two human-facing strings in the `seed_catalog` management command (help text / docstring) that say "seed/" to say "data/".

## Capabilities

### New Capabilities
<!-- None — repository housekeeping; the seeding behavior is unchanged. -->

### Modified Capabilities
<!-- None at the spec/behavior level. -->

## Impact

- Files: `backend/seed/*.csv` → `backend/data/*.csv`; `backend/core/seeds/csv_catalog.py` (path constant); `backend/core/management/commands/seed_catalog.py` (help text).
- The `seed_catalog` management command continues to discover the same CSVs at the new location.
- Not in scope: moving CSVs to git-lfs/fixtures (deferred — 1.2MB stays in git to avoid adding LFS setup for collaborators).
