## Context

The backend is Django 5 + DRF + Celery. No `pyproject.toml` exists at repo root; deps live in `backend/requirements.txt`. There is no pre-commit framework and no type checker. Coverage of type hints is partial (~43% of defs annotated). Goal: enforce types going forward without blocking on a full annotation backfill.

## Goals

- Static type checking runs locally on every commit and passes green on the current tree.
- Django-aware: pyright resolves `models.Model` fields, managers, querysets sensibly.
- Zero production-code changes; dev-only footprint.

## Decisions

### Checker: pyright (not mypy)
Chosen by the user. Fast, no separate plugin needed for basic Django support when paired with `django-types`. Distributed as a pip package (`pyright`) that bootstraps its own node-based binary.

### Django stubs: `django-types` + `djangorestframework-stubs`
`django-types` is the lighter, pyright-oriented Django stub package (no mypy plugin requirement). `djangorestframework-stubs` was added after measurement: with deps installed, standard mode produced 39 errors that were **all** DRF false positives (`get_queryset`/`get_serializer_class` overrides, `validated_data` subscripting seen as possibly-None). Adding DRF stubs cleared 37 of them, letting the correctness rules they touch (`reportOptionalSubscript`, `reportIndexIssue`, `reportIncompatibleMethodOverride` at most sites) stay at `error` rather than being blanket-downgraded. Net: stubs over suppression wherever a stub package exists.

### Type-checking mode: `standard`
User-selected. More thorough than `basic`. To keep the current tree green at `standard` without annotating code, suppress noise that is purely about missing third-party stubs rather than real type errors:
- `reportMissingTypeStubs: "none"` and `reportMissingModuleSource: "none"` — celery/openai/redis/etc. have no stubs (DRF is covered by `djangorestframework-stubs`); these would otherwise be reported.
- `reportAttributeAccessIssue` / dynamic-Django diagnostics are left at standard defaults but validated against the tree; if specific standard-mode diagnostics fire on legitimate Django dynamic patterns, downgrade only those specific rules to `"warning"` (warnings do not fail the hook by default) rather than weakening the whole mode.
- Exclude `**/migrations`, `frontend/`, `**/__pycache__`, virtualenvs, and `**/node_modules`.

The acceptance bar: `pyright` exits 0 (no errors) on the repo at `standard`. Warnings are acceptable.

### Hook: pre-commit framework
`.pre-commit-config.yaml` with a hook that runs pyright. Use a `local` repo hook invoking the installed `pyright` (`entry: pyright`, `language: system`, `pass_filenames: false`, `types: [python]`) so it checks the configured project rather than only staged file paths — this avoids false greens when a change in file A breaks types in file B. Requires the dev to have installed `requirements-dev.txt` and run `pre-commit install`.

### Config location: `pyrightconfig.json` at repo root
No `pyproject.toml` exists; adding a standalone `pyrightconfig.json` is the least-invasive option and keeps pyright config out of runtime packaging. `include: ["backend"]`.

## Risks / Trade-offs

- **DRF stubs coverage partial** → `djangorestframework-stubs` was added (cleared 37 of 39 DRF false-positive errors). 2 residual diagnostics (`reportReturnType` on `ReturnDict`, `reportIncompatibleMethodOverride` on framework overrides) are downgraded to warning. Celery/openai/redis remain stubless; `reportMissingTypeStubs`/`reportMissingModuleSource: "none"` silence that noise.
- **Hook requires manual `pre-commit install`** → not automatic on clone. Documented in README/proposal. Accepted.
- **Standard mode may surface real latent errors** in current code. If so, the tooling-only scope means we fix them minimally or scope the specific diagnostic to `warning`; we do not mass-annotate.

## Migration / Rollout

1. Add dev deps + configs.
2. Run pyright locally; tune config until green.
3. Contributors run `pip install -r backend/requirements-dev.txt && pre-commit install`.
