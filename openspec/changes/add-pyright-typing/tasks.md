# Tasks

## 1. Dev dependencies
- [x] 1.1 Create `backend/requirements-dev.txt` with `-r requirements.txt`, `pyright`, `django-types`, `pre-commit` (pinned with compatible-range specifiers matching repo style).

## 2. Pyright configuration
- [x] 2.1 Create repo-root `pyrightconfig.json`: `include: ["backend"]`, `typeCheckingMode: "standard"`, exclude migrations/frontend/`__pycache__`/node_modules/venv, and silence missing-third-party-stub reports (`reportMissingTypeStubs`, `reportMissingModuleSource`).
- [x] 2.2 Run pyright against the tree; if real `standard`-mode errors fire on legitimate Django dynamic patterns, downgrade only those specific diagnostics to `warning`. Do NOT annotate production code.
- [x] 2.3 Confirm `pyright` exits 0 with 0 errors.

## 3. Pre-commit hook
- [x] 3.1 Create `.pre-commit-config.yaml` with a `local` pyright hook (`language: system`, `entry: pyright`, `pass_filenames: false`, `types: [python]`).
- [x] 3.2 Verify the hook runs and reports green on the current tree (`pre-commit run pyright --all-files` or equivalent if pre-commit installed; otherwise run `pyright` directly).

## 4. Docs
- [x] 4.1 Add a short "Type checking" note to `README.md` (or backend README): install `requirements-dev.txt`, run `pre-commit install`, hook runs pyright on commit.

## 5. Validation
- [x] 5.1 `openspec validate add-pyright-typing --strict` passes.
- [x] 5.2 Existing backend test suite still imports/runs (no production code changed): `cd backend && python -m pytest` (or note if env unavailable).
