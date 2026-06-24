## 1. Confirm physical table names

- [x] 1.1 Run `docker compose run --rm backend python manage.py dbshell -- -c "\dt core_*"` (or inspect `sqlmigrate`) to record the exact current table names for the 7 moving models.

## 2. Create literature/models package

- [x] 2.1 Create `backend/literature/models/__init__.py` re-exporting all moved models + their enums.
- [x] 2.2 Move `LiteratureReference`, `CompoundLiterature`, `CompoundRelationship` (+ `RelevanceCategory`, `RoleInPaper`, `RelationshipType`, `LiteratureEnrichmentStatus`) into `literature/models/literature.py`; import `SourceMetadata` from `core.models.metadata`.
- [x] 2.3 Move `LiteratureDiscoveryTarget`, `LiteratureDiscoveryEvent` (+ all `Discovery*` enums/constants) into `literature/models/discovery_target.py`.
- [x] 2.4 Move `InteractionRule`, `InteractionAssertion` (+ `InteractionType`, `RiskClass`) into `literature/models/interactions.py`; import `SourceMetadata` from core.
- [x] 2.5 On each moved model, pin `Meta.db_table` to its existing physical name from task 1.1 (e.g. `db_table = "core_literaturereference"`).
- [x] 2.6 Keep all FKs to core models as string refs (`"core.Compound"`, `"core.Formulation"`, `"core.Product"`).

## 3. Remove from core

- [x] 3.1 Delete `core/models/literature.py`, `core/models/literature_discovery_target.py`, `core/models/interactions.py`.
- [x] 3.2 Remove the corresponding imports and `__all__` entries from `core/models/__init__.py`.

## 4. Repoint all importers

- [x] 4.1 Core side: update `core/admin.py`, `core/tasks.py`, `core/tests/test_tasks.py` to import moved models from `literature.models`.
- [x] 4.2 Literature side: update `literature/discovery.py`, `literature/enrichment/literature_agent.py`, `literature/ingestion/ingest.py`, `literature/management/commands/enrich_literature.py`, `literature/seeds/loader.py`, and `literature/tests/*` to import from `literature.models`.
- [x] 4.3 Grep the full `backend/` tree for each moved model name and repoint any stragglers (serializers, views).

## 5. Write migrations (state-only)

- [x] 5.1 Create `literature/migrations/__init__.py` and `literature/migrations/0001_initial.py`: `SeparateDatabaseAndState(state_operations=[CreateModel x7], database_operations=[])`, `dependencies=[('core','0017_literaturediscoverytarget_literaturediscoveryevent_and_more')]`.
- [x] 5.2 Create `core/migrations/0018_remove_literature_models.py`: `SeparateDatabaseAndState(state_operations=[DeleteModel x7], database_operations=[])`, `dependencies=[('core','0017_...'), ('literature','0001_initial')]`.
- [x] 5.3 Confirm `manage.py makemigrations --check --dry-run` reports no further changes (definitions match state).

## 6. Verify

- [x] 6.1 `manage.py sqlmigrate literature 0001_initial` — assert no `CREATE TABLE`/`DROP TABLE`.
- [x] 6.2 On a DB seeded with literature/interaction/discovery rows: record row counts, run `manage.py migrate`, confirm counts and FK resolution unchanged.
- [x] 6.3 `manage.py check` — no errors; confirm `from core.models import LiteratureReference` now fails.
- [x] 6.4 `manage.py test core.tests literature.tests` — all pass.
