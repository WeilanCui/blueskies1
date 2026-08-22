# static-type-checking Specification

## Purpose

Define what the pyright static type-checking gate enforces for this codebase: genuinely-real type-safety warnings are fixed at their source with behavior-preserving changes, runtime behavior is left unchanged, and warnings that stem from stub-vs-pinned-library version mismatches are deliberately not "fixed" in code.
## Requirements
### Requirement: Real type-safety warnings are fixed at source

The genuinely-real pyright warnings (not stub/framework limitations) SHALL be resolved by behavior-preserving source fixes.

#### Scenario: seed_catalog return type narrowed

- WHEN pyright analyzes `core/management/commands/seed_catalog.py`
- THEN there is no `reportAttributeAccessIssue` for `.items()` on `int`, because `seed_catalog()` is typed `dict[str, dict[str, int]]`

#### Scenario: injected callable guarded

- WHEN pyright analyzes the two `self.ingest_compound_func(...)` call sites in `literature/discovery.py`
- THEN no `reportOptionalCall` is reported

#### Scenario: ElementTree text narrowed

- WHEN pyright analyzes `literature/ingestion/pubmed_client.py`
- THEN no `reportOptionalMemberAccess` is reported for `.text`

#### Scenario: test narrows optional before access

- WHEN pyright analyzes `literature/tests/test_literature_agent.py`
- THEN no `reportOptionalMemberAccess` is reported for `extraction`

### Requirement: Behavior is unchanged

The fixes SHALL NOT alter runtime behavior.

#### Scenario: system check and gate still pass

- WHEN `python manage.py check` and `pyright` are run with deps installed
- THEN the system check reports no issues and pyright reports 0 errors

### Requirement: Stub-version mismatches are not "fixed" in code

Warnings caused by a stub modeling a newer library API than the pinned dependency SHALL NOT be resolved by changing code in a way that breaks the pinned runtime.

#### Scenario: CheckConstraint left as-is

- WHEN the `CheckConstraint(check=...)` sites in `core/models/literature_discovery_target.py` are considered
- THEN the code keeps `check=` (correct for Django `<5.1`) and the warning is left for the sibling suppression change

### Requirement: Pyright configuration

The repository SHALL include a `pyrightconfig.json` at the repo root that scopes static type checking to the Django backend at `standard` type-checking mode.

#### Scenario: Config scopes to backend

- WHEN pyright runs using the repo-root `pyrightconfig.json`
- THEN it analyzes the `backend/` directory and excludes migrations, `frontend/`, virtualenvs, `__pycache__`, and `node_modules`

#### Scenario: Standard mode is configured

- WHEN the `pyrightconfig.json` is read
- THEN `typeCheckingMode` is `standard`

### Requirement: Django-aware type stubs

The dev tooling SHALL include `django-types` and `djangorestframework-stubs` so pyright resolves Django ORM and DRF constructs.

#### Scenario: stub packages are declared dev dependencies

- WHEN `backend/requirements-dev.txt` is inspected
- THEN it lists `django-types` and `djangorestframework-stubs`

### Requirement: Clean baseline on current tree

Running pyright on the repository at the configured mode SHALL report zero errors on the current codebase (warnings permitted).

#### Scenario: Pyright passes green

- WHEN `pyright` is run from the repo root
- THEN it exits with code 0 and reports 0 errors

### Requirement: Pre-commit pyright gate

The repository SHALL provide a `.pre-commit-config.yaml` that runs pyright on commit via the pre-commit framework.

#### Scenario: Hook is defined

- WHEN `.pre-commit-config.yaml` is inspected
- THEN it defines a hook that invokes pyright over the project and is configured not to pass individual staged filenames

#### Scenario: Commit with type error is blocked

- WHEN a contributor has run `pre-commit install` and attempts to commit code that introduces a pyright error
- THEN the commit is rejected with the pyright diagnostic

### Requirement: Dev dependency manifest

The repository SHALL capture the new dev tooling in `backend/requirements-dev.txt`.

#### Scenario: Manifest lists tooling

- WHEN `backend/requirements-dev.txt` is inspected
- THEN it lists `pyright`, `django-types`, `djangorestframework-stubs`, and `pre-commit`

### Requirement: Model relation/FK warnings resolved by real annotations

`reportAttributeAccessIssue` warnings for Django reverse relations and `<fk>_id` attributes SHALL be resolved with bare class-level annotations on the model classes, typed from the actual ForeignKey definitions.

#### Scenario: reverse relation annotated correctly

- WHEN a model is the target of `ForeignKey(target, related_name="rel")`
- THEN the target model declares `rel: Manager[SourceModel]` and pyright no longer reports `reportAttributeAccessIssue` for `target_instance.rel`

#### Scenario: foreign-key id annotated

- WHEN a model declares `fk = ForeignKey(...)`
- THEN the model declares `fk_id: int` and pyright no longer reports the `<fk>_id` access

#### Scenario: annotations have no runtime effect

- WHEN the annotations are added
- THEN they are bare (no assignment), `Manager` is imported under `TYPE_CHECKING`, and `python manage.py makemigrations --check --dry-run` reports no new migrations

### Requirement: Un-annotatable warnings use rule-specific ignores

Warnings that cannot be expressed as a correct annotation SHALL use a rule-specific `# pyright: ignore[<rule>]` (not blanket `# type: ignore`).

#### Scenario: framework/stub residual ignored specifically

- WHEN a warning is from django-environ overloads, DRF ReturnDict/overrides, DRF test-client attributes, abstract-model Meta, the CheckConstraint stub mismatch, or celery `.delay`
- THEN that line carries a rule-specific `# pyright: ignore[<rule>]`

### Requirement: Zero-warning baseline with no behavior change

After this change the gate SHALL report 0 errors and 0 warnings, with no runtime behavior change.

#### Scenario: gate clean and app boots

- WHEN `pyright` and `python manage.py check` are run in the venv
- THEN pyright reports 0 errors and 0 warnings and the system check reports no issues

### Requirement: Mutually exclusive with the suppress change

This change and the sibling suppress change SHALL NOT both be merged.

#### Scenario: only one approach lands

- WHEN choosing between this annotate change and the suppress change
- THEN exactly one is merged

### Requirement: Zero-warning baseline via targeted suppression

Every remaining framework/stub-limitation warning SHALL be suppressed at its source with a rule-specific `# pyright: ignore[<rule>]` comment, bringing the gate to zero warnings.

#### Scenario: gate reports no warnings

- WHEN `pyright` is run in the project venv after this change
- THEN it reports 0 errors and 0 warnings

#### Scenario: suppressions are rule-specific

- WHEN a suppression comment is inspected
- THEN it names the specific rule(s) being ignored (e.g. `# pyright: ignore[reportAttributeAccessIssue]`), not a blanket `# type: ignore`

#### Scenario: unrelated errors still surface

- WHEN a new, different type error is introduced on a line that carries a rule-specific ignore
- THEN pyright still reports that new error

### Requirement: No behavior change

The suppression SHALL be comment-only with no runtime effect.

#### Scenario: system check passes

- WHEN `python manage.py check` runs with deps installed
- THEN it reports no issues

### Requirement: Mutually exclusive with the annotate change

This change and the sibling annotate change SHALL NOT both be merged.

#### Scenario: only one approach lands

- WHEN choosing between this suppression change and the annotate change
- THEN exactly one is merged to resolve the remaining warnings

