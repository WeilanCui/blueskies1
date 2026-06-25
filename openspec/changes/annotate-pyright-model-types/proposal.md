## Why

After the real-warning fixes (PR #32), the pyright gate reports ~277 warnings. The largest, most legitimate slice — `reportAttributeAccessIssue` (189) — is django-types failing to synthesize Django reverse-relation accessors (e.g. `compound.identifiers`) and foreign-key `_id` attributes. These are best resolved with REAL type annotations on the model classes, which is both correct documentation and clears every downstream access (tests, views, serializers) at once. This is the annotation-first alternative to the sibling suppression change.

## What Changes

- Add bare class-level type annotations to Django model classes for the accessors django-types does not generate:
  - Reverse relations: `related_name: Manager[RelatedModel]` (resolved from the actual `ForeignKey(..., related_name="...")` definition).
  - Foreign-key id attributes: `<fk>_id: int`.
  - Explicit `id: int` where the auto pk is flagged.
  - Annotations are bare (no assignment) and therefore have zero runtime effect; `Manager` is imported under `TYPE_CHECKING`.
- For warnings that genuinely cannot be expressed as a correct annotation — django-environ `env()` overloads (`config/settings.py`), DRF `ReturnDict`/override patterns (`core/serializers.py`, `core/views.py`), DRF test-client attributes (`response.data`, `force_authenticate`), abstract-model `Meta` inheritance, the CheckConstraint stub-version mismatch, and celery `.delay` — fall back to a rule-specific `# pyright: ignore[<rule>]` with intent clear from context.
- Net result: 0 errors / 0 warnings, with the dominant relation/FK noise resolved by real types rather than blanket ignores.
- ALTERNATIVE to the sibling suppress change (#PR2); merge only one.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `static-type-checking`: resolve the relation/FK warnings with real model annotations; reach a zero-warning baseline.

## Impact

- Production code: model files gain type annotations (documentation value beyond pyright). Other files: a small number of rule-specific ignores for genuinely un-annotatable framework/test cases.
- No runtime behavior change (bare annotations + comments).
- Builds on PR #32. Mutually exclusive with the suppress change.
