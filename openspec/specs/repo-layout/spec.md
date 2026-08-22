# repo-layout Specification

## Purpose
TBD - created by archiving change move-build-deck. Update Purpose after archive.
## Requirements
### Requirement: Standalone tooling lives under tools/scripts

Non-application, standalone scripts SHALL NOT reside at the repository root. The pitch-deck generator SHALL live at `tools/scripts/build_deck.py`.

#### Scenario: build_deck relocated

- **WHEN** inspecting the repository tree
- **THEN** `build_deck.py` does not exist at the repo root
- **AND** `tools/scripts/build_deck.py` exists with identical content

#### Scenario: No references break

- **WHEN** grepping the repo for `build_deck`
- **THEN** no source file, Docker build, CI config, or doc references the old root path

### Requirement: Raw seed data dir is named data, not seed

Raw CSV seed data SHALL live in `backend/data/`, not `backend/seed/`, so it does not collide with the `core/seeds/` and `literature/seeds/` code packages.

#### Scenario: Directory renamed

- **WHEN** inspecting the backend tree
- **THEN** `backend/seed/` does not exist
- **AND** `backend/data/` contains the 5 CSVs (AB1, AB2, Prod1, Prod2, red1)

### Requirement: Seed catalog command finds CSVs at the new path

The `seed_catalog` command and `core/seeds/csv_catalog` helpers SHALL resolve the renamed directory with no behavior change.

#### Scenario: CSV discovery unchanged

- **WHEN** `discover_csv_files()` runs with no explicit `seed_dir`
- **THEN** it returns the 5 CSV files from `backend/data/`

#### Scenario: No stale path references

- **WHEN** grepping backend for a filesystem path ending in `/ "seed"`
- **THEN** there are no matches; the path constant points at `data`

### Requirement: Model exports are alphabetically ordered

`core/models/__init__.py` SHALL list its import blocks (by module), the names within each block, and `__all__` in alphabetical order, while preserving the exact set of exported names.

#### Scenario: Ordering is alphabetical

- **WHEN** reading `core/models/__init__.py`
- **THEN** the `from core.models.<module>` blocks appear in alphabetical module order
- **AND** the names imported within each block are in alphabetical order
- **AND** `__all__` is in alphabetical order

#### Scenario: Export set unchanged

- **WHEN** comparing the set of names in `__all__` before and after the change
- **THEN** the two sets are identical (no name added or removed)
- **AND** `manage.py check` reports no issues and `makemigrations --check` detects no changes

### Requirement: Serializers are organized as a per-domain package

`core/serializers` SHALL be a package whose submodules group serializers by domain (mirroring `core/models/`), with `core/serializers/__init__.py` re-exporting the full public surface so existing `from core.serializers import …` imports keep working.

#### Scenario: Per-domain submodules exist

- **WHEN** reading `backend/core/serializers/`
- **THEN** it is a package (contains `__init__.py`)
- **AND** each serializer lives in a domain submodule mirroring `core/models/` (e.g. `compound`, `auth`, `location`, `formulation`, `routine`, `daily_checkin`, `reaction`, `catalog`, `intake`, `product`, `contact`)
- **AND** each non-private helper function lives in the submodule of its related serializers

#### Scenario: Public import surface unchanged

- **WHEN** comparing the set of names importable from `core.serializers` before and after the change
- **THEN** every name previously importable (e.g. `CompoundSerializer`, `RoutineAddProductSerializer`, `auth_user_payload`, `catalog_slug`, `serialize_catalog_product`, `intake_payload`) is still importable from `core.serializers`
- **AND** no serializer field, validation rule, or method body is altered

#### Scenario: Importers and app load unaffected

- **WHEN** `core/views.py` and the test suite import from `core.serializers`
- **THEN** the imports resolve without modification to the importing files
- **AND** `manage.py check` reports no issues
- **AND** the existing test suite passes

