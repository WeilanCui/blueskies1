## Context

The `literature` app has ingestion/enrichment code and seeds but no `models/` and no `migrations/`. All literature-domain models live in `core/models/` and were created by core migrations `0003` (literature refs), interaction migrations, and `0017` (discovery). The only core→literature-model coupling is `core.ProfileConstraint` → `PropertyDefinition`, so `properties.py` must stay in core. Moving models between Django apps changes their default table name (`core_x` → `literature_x`), which is where the data-safety risk lives.

## Goals / Non-Goals

**Goals:**
- `literature` app owns `LiteratureReference`, `CompoundLiterature`, `CompoundRelationship`, `LiteratureDiscoveryTarget`, `LiteratureDiscoveryEvent`, `InteractionRule`, `InteractionAssertion`.
- Zero data loss; existing rows and FK values untouched.
- All importers repointed; `core.models` no longer exports the moved models.

**Non-Goals:**
- No field/behavior/Meta changes (other than an explicit `db_table` pin — see below).
- Do NOT move `properties.py`, `compound.py`, `metadata.py`, or any core identity model.
- No API/serializer response shape changes.

## Decisions

- **Scope line.** Move only models whose sole consumers are the literature pipeline + read APIs. `PropertyDefinition`/`PropertyAssertion`/`GlossaryTerm` stay in core because `ProfileConstraint` (a core profile feature) FKs `PropertyDefinition`; moving them would create a core→literature dependency for a core feature.

- **`SourceMetadata` stays in core, imported cross-app.** It is an abstract base (no table) shared by core `PropertyAssertion` and the moved `CompoundLiterature`/`CompoundRelationship`/`InteractionAssertion`. Moved modules do `from core.models.metadata import SourceMetadata`. Cross-app import of an abstract mixin is acceptable and introduces no DB coupling.

- **State-only move via `SeparateDatabaseAndState` + pinned `db_table` (primary, safest).** Each moved model sets `Meta.db_table` to its current physical name (`core_literaturereference`, `core_compoundliterature`, `core_compoundrelationship`, `core_literaturediscoverytarget`, `core_literaturediscoveryevent`, `core_interactionrule`, `core_interactionassertion` — confirm via `sqlmigrate`/`\dt` first). Then:
  1. `literature/migrations/0001_initial.py`: `SeparateDatabaseAndState(state_operations=[CreateModel(...) x7], database_operations=[])`, `dependencies=[('core','0017_...')]`. Registers ownership in `literature` state without creating tables.
  2. `core/migrations/0018_*.py`: `SeparateDatabaseAndState(state_operations=[DeleteModel x7], database_operations=[])`, `dependencies=[('core','0017_...'), ('literature','0001_initial')]`. Removes from `core` state without dropping tables.
  Because `db_table` is pinned, both states map to the unchanged physical tables — **no rename, no row movement, no FK rewrite**.

- **Cross-app FK migration deps.** Models referencing `core.Compound`/`Formulation`/`Product` by string already migrate cleanly; the `CreateModel` state ops record those FKs and Django resolves them via the dependency on core `0017`.

- **Physical rename is a separate, optional follow-up.** Renaming `core_*` → `literature_*` for cosmetic consistency is deferred; it adds rename ops + FK constraint churn with no functional benefit. Out of scope here.

## Risks / Trade-offs

- **State/table mismatch if `db_table` not pinned** → silent "relation does not exist" at query time. Mitigation: pin `db_table`, and verify with `manage.py sqlmigrate literature 0001` (must show no `CREATE TABLE`) and `migrate --plan`.
- **Missed importer** → ImportError at boot. Mitigation: grep the full tree for each moved model name; repoint; run `manage.py check` and full test suite.
- **Migration applied to an empty dev DB hides bugs.** Mitigation: validate against a DB seeded with literature/interaction/discovery rows; assert row counts unchanged before/after `migrate`.
- **Cosmetic debt**: literature tables keep `core_` prefix. Accepted; documented as deferred follow-up.
