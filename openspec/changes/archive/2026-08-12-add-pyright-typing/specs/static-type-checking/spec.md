## ADDED Requirements

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
