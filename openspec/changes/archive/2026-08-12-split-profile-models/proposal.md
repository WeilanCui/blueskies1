## Why

`core/models/profiles.py` aggregates three models (`Profile`, `SkinProfile`, `ProfileConstraint`) plus seven `TextChoices` enums in one file. This directly violates the project's own model-file convention (`.cursor/rules/django-model-files.mdc`), which names `profiles.py` as the canonical BAD example and `SkinProfile → skin_profile.py` as the intended layout. Splitting it brings the codebase in line with the one-model-per-file rule already applied to every other model.

## What Changes

- Split `core/models/profiles.py` into one module per primary model:
  - `profile.py` — `Profile` + `ProfileVisibility`
  - `skin_profile.py` — `SkinProfile` + `SkinType`, `FitzpatrickSkinType`, `PregnancyStatus`
  - `profile_constraint.py` — `ProfileConstraint` + `ProfileConstraintKind`, `ConstraintEnforcement`, `ConstraintSeverity`
- Each `TextChoices` enum moves into the file of its sole consuming model.
- Update `core/models/__init__.py` to import the same names from the new modules; public `__all__` is unchanged so `from core.models import X` keeps working.
- Update any direct `from core.models.profiles import …` imports to the new module paths.
- Delete `core/models/profiles.py`.
- No schema change — same app label + class names mean no migration (file-only move per the cursor rule).

## Capabilities

### New Capabilities
<!-- None — internal file reorganization with no behavior change. -->

### Modified Capabilities
<!-- None — model fields, Meta, methods, and DB schema are unchanged. -->

## Impact

- Code: `backend/core/models/profiles.py` (removed) → `profile.py`, `skin_profile.py`, `profile_constraint.py`; `backend/core/models/__init__.py`.
- Consumers using `from core.models import …` are unaffected. Any direct `core.models.profiles` imports (e.g. in `core/profiles/`, `core/serializers.py`, `core/admin.py`, tests) must be repointed.
- No migration, no API change, no DB change. Existing model tests (`core/tests/test_profile_constraints.py`) must still pass.
