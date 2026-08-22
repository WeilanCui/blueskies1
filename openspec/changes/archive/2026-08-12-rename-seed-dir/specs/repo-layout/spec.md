## ADDED Requirements

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
