## Why

The `literature` Django app owns zero models: every literature-domain model lives in `core/models/`, while the `literature` app (ingestion + enrichment) imports `core.models` heavily. This inverts the app boundary — `literature` reads as a service package, not a Django app — and leaves ownership of models like `LiteratureReference` ambiguous. We are establishing a real boundary by relocating the unambiguously literature-domain models into `literature/models/`.

## What Changes

- Create `literature/models/` and a `literature/migrations/` package, and move these models from `core` into `literature`:
  - `literature.py` → `LiteratureReference`, `CompoundLiterature`, `CompoundRelationship`
  - `literature_discovery_target.py` → `LiteratureDiscoveryTarget`, `LiteratureDiscoveryEvent`
  - `interactions.py` → `InteractionRule`, `InteractionAssertion`
- **Keep in `core`** (deliberately): `Compound`/`ChemicalClass`/`Formulation`/`Product` (core identity), `metadata.py` `SourceMetadata` (abstract base shared by both apps), and `properties.py` `PropertyDefinition`/`PropertyAssertion`/`GlossaryTerm` — because `core.ProfileConstraint` FKs `PropertyDefinition`, so it is core-consumed vocabulary.
- Moved models keep their cross-app FKs to `core.*` via string references (already used).
- Migrate model ownership with `SeparateDatabaseAndState` so **no data is moved or dropped** — only Django's app registry ownership changes; physical tables are renamed `core_*` → `literature_*` as a database-only operation.
- Update `core/models/__init__.py` to stop exporting the moved models; update all importers (`from core.models import …` and any direct paths) to import from `literature.models`.
- **BREAKING** (internal): the moved models are no longer importable from `core.models`.

## Capabilities

### New Capabilities
- `literature-domain-models`: the `literature` app owns its persistent literature/interaction/discovery models, with migrations, while continuing to reference core identity models by FK.

### Modified Capabilities
<!-- None at the spec/behavior level — model fields and DB rows are unchanged. -->

## Impact

- Code: `backend/literature/models/` (new), `backend/literature/migrations/` (new), removal of `core/models/literature.py`, `literature_discovery_target.py`, `interactions.py`; edits to `core/models/__init__.py`.
- Imports: any module importing these models — `core/serializers.py`, `core/admin.py`, `core/views.py`, `literature/ingestion/*`, `literature/enrichment/*`, `literature/discovery.py`, tests — must repoint to `literature.models`.
- DB: table renames via state-preserving migrations; no row loss, no FK data change. Requires careful cross-app migration dependencies.
- Risk: this is a schema-ownership migration — must be validated against a populated database before merge.
