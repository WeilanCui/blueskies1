# literature-domain-models Specification

## Purpose
TBD - created by archiving change literature-app-boundary. Update Purpose after archive.
## Requirements
### Requirement: Literature app owns its domain models

The `literature` Django app SHALL define the literature, interaction, and discovery models in `backend/literature/models/` and SHALL have its own `migrations/` package. The models `LiteratureReference`, `CompoundLiterature`, `CompoundRelationship`, `LiteratureDiscoveryTarget`, `LiteratureDiscoveryEvent`, `InteractionRule`, and `InteractionAssertion` SHALL belong to the `literature` app label. They SHALL NOT be importable from `core.models`.

#### Scenario: Moved models belong to the literature app

- **WHEN** Django loads the app registry
- **THEN** each moved model's `_meta.app_label` is `"literature"`
- **AND** `from core.models import LiteratureReference` raises `ImportError`

#### Scenario: Core identity and vocabulary models stay in core

- **WHEN** inspecting app labels
- **THEN** `Compound`, `ChemicalClass`, `Formulation`, `Product`, `PropertyDefinition`, `PropertyAssertion`, and `GlossaryTerm` remain in the `core` app
- **AND** `core.ProfileConstraint`'s FK to `PropertyDefinition` resolves without importing `literature`

### Requirement: Move preserves all data and foreign keys

The ownership move SHALL NOT lose, recreate, or rewrite any rows. Migrations SHALL use state-only operations so the physical tables and their foreign-key values are unchanged.

#### Scenario: No table creation or drop in the move

- **WHEN** `manage.py sqlmigrate literature 0001_initial` is run
- **THEN** the SQL contains no `CREATE TABLE` or `DROP TABLE` for the moved models

#### Scenario: Row counts unchanged after migration

- **WHEN** `manage.py migrate` is applied to a database populated with literature, interaction, and discovery rows
- **THEN** the row count of every moved model's table is identical before and after
- **AND** existing foreign keys to `core.Compound`/`core.Formulation`/`core.Product` still resolve

### Requirement: All consumers reference the new location

Every importer of a moved model SHALL import it from `literature.models`, and the system SHALL pass `manage.py check` and the existing test suite.

#### Scenario: System check and tests pass after repointing

- **WHEN** `manage.py check` and `manage.py test core.tests literature.tests` run after the move
- **THEN** there are no import errors and all tests pass

