## ADDED Requirements

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
