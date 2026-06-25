## Why

The Django backend has only ~43% return-type annotation coverage and **no static type checker** — nothing verifies the annotations that do exist, and type regressions ship silently. Standing up pyright with Django stubs and a pre-commit gate makes types real and enforced going forward, without requiring a mass-annotation effort up front.

## What Changes

- Add `pyright` as a dev dependency and a repo-level `pyrightconfig.json` configured at `standard` type-checking mode, scoped to `backend/`.
- Add `django-types` so pyright understands Django ORM/model constructs.
- Add a `pre-commit` framework config (`.pre-commit-config.yaml`) with a pyright hook that runs on every commit.
- Add `backend/requirements-dev.txt` capturing the new dev tooling (pyright, django-types, pre-commit).
- Tune pyright config so the existing codebase passes cleanly at `standard` mode (suppress third-party missing-stub noise for libs without stubs, e.g. DRF/celery; exclude migrations, frontend, virtualenvs). No production code annotations are added in this change.

## Capabilities

### New Capabilities
- `static-type-checking`: Repository-wide static type analysis of the Django backend via pyright, with Django-aware stubs and an enforced pre-commit gate.

### Modified Capabilities
<!-- none -->

## Impact

- New dev dependencies: `pyright`, `django-types`, `pre-commit` (dev-only; no runtime/production impact).
- New files: `pyrightconfig.json`, `.pre-commit-config.yaml`, `backend/requirements-dev.txt`.
- Contributors must run `pre-commit install` once to activate the hook.
- No application code behavior changes; no migrations; no API changes.
