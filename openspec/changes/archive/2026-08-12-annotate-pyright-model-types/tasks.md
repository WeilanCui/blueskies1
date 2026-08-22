# Tasks

## 1. Model annotations
- [x] 1.1 For each Django model flagged with reverse-relation `reportAttributeAccessIssue`, find the `ForeignKey(..., related_name="X")` that creates it and add `X: Manager[SourceModel]` on the target model (bare annotation).
- [x] 1.2 For each flagged `<fk>_id`, add `<fk>_id: int` on the declaring model.
- [x] 1.3 Add `id: int` where the pk is flagged.
- [x] 1.4 Ensure each annotated model file has `from __future__ import annotations` and imports `Manager` (and any model classes used only in annotations) under `if TYPE_CHECKING:`.

## 2. Un-annotatable residual
- [x] 2.1 Apply rule-specific `# pyright: ignore[<rule>]` to genuinely un-annotatable sites: django-environ `env()` (settings), DRF ReturnDict/overrides (serializers/views), DRF test-client attrs, abstract-model Meta, CheckConstraint `check=`, celery `.delay`.

## 3. Validation
- [x] 3.1 `pyright` in venv → 0 errors, 0 warnings.
- [x] 3.2 `python manage.py makemigrations --check --dry-run` → no new migrations.
- [x] 3.3 `python manage.py check` → no issues.
- [x] 3.4 `openspec validate annotate-pyright-model-types --strict` passes.
