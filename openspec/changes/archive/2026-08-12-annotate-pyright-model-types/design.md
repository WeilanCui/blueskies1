## Context

django-types provides field typing but does not synthesize reverse-relation managers or `<fk>_id` attributes. These produce the bulk (189) of the gate's warnings as `reportAttributeAccessIssue`. Real annotations on the models fix them correctly and document the schema, and resolve every downstream access site at once.

## Decisions

### Bare class-level annotations on models
- Reverse relation: on the model that is the FK *target*, add `related_name: Manager[SourceModel]` where `SourceModel` is the model declaring `ForeignKey(target, related_name="related_name")`. The type MUST be resolved from the actual FK definition, not guessed.
- FK id: `<fk>_id: int` on the model declaring the `ForeignKey`.
- pk: `id: int` only where flagged.
- Annotations are bare (no value assigned) → no runtime effect, no migration impact. `Manager` (and model classes used only in annotations) imported under `if TYPE_CHECKING:` with `from __future__ import annotations` so names are strings at runtime.

### Correctness over coverage
Each reverse-relation annotation's type parameter must match the real related model. A wrong type would still silence pyright (the attribute simply exists) but would be misleading — so correctness is verified in review against the FK definitions.

### Fall back to ignores only where annotation is impossible
These cannot be expressed as a correct annotation and get rule-specific `# pyright: ignore[<rule>]`:
- `config/settings.py` django-environ `env()` overload mismatches (`reportArgumentType`).
- DRF `ReturnDict` returns / field declaration / method overrides (`core/serializers.py`, `core/views.py`).
- DRF test client attributes `response.data`, `force_authenticate`, `_create_formsets` (test framework).
- Abstract-model `Meta` inheritance (`reportIncompatibleVariableOverride`).
- CheckConstraint `check=` stub-version mismatch (`reportCallIssue`) — correct for Django <5.1.
- celery `@shared_task` `.delay` (`reportFunctionMemberAccess`).
TextChoices `reportArgumentType` sites are reviewed case-by-case: fixed with `.value`/cast where that is the genuine intent, otherwise ignored.

## Risks / Trade-offs

- **Annotation correctness** is not enforced by pyright (a wrong relation type still type-checks). Mitigated by deriving each from the FK definition and verifying in review.
- **More invasive than the suppress change** in the model files, but the annotations carry real documentation value. The suppress change is the lower-churn alternative; only one is merged.
- `from __future__ import annotations` + `TYPE_CHECKING` imports keep runtime untouched.

## Verification

- `pyright` in venv → 0 errors, 0 warnings.
- `manage.py check` passes; no new migrations (`makemigrations --check --dry-run` clean) since annotations are not fields.
