## Context

`backend/core/models/profiles.py` holds `Profile`, `SkinProfile`, `ProfileConstraint`, and seven `TextChoices` enums. Every other model in `core/models/` already follows one-model-per-file; `profiles.py` is the lone holdout and is the exact anti-pattern called out in `.cursor/rules/django-model-files.mdc`. Five modules import directly from `core.models.profiles` (`routine.py`, `location.py`, `reaction.py`, `daily_checkin.py`, and `__init__.py`); the rest of the codebase imports via the `core.models` package.

## Goals / Non-Goals

**Goals:**
- One primary model per module: `profile.py`, `skin_profile.py`, `profile_constraint.py`.
- Co-locate each single-consumer enum with its model.
- Keep the public import surface (`from core.models import …`) and `__all__` identical.
- Zero schema change → zero migration.

**Non-Goals:**
- No field, `Meta`, method, validation, or behavior changes.
- No renames of models or enums.
- No change to serializers, views, or API shape.

## Decisions

- **Enum placement by sole consumer.** `ProfileVisibility` → `profile.py`; `SkinType`, `FitzpatrickSkinType`, `PregnancyStatus` → `skin_profile.py`; `ProfileConstraintKind`, `ConstraintEnforcement`, `ConstraintSeverity` → `profile_constraint.py`. None of these enums is shared across the three models, so no shared `*_choices.py` is needed.
- **Dependency direction.** `skin_profile.py` and `profile_constraint.py` import `Profile` from `core.models.profile`. `ProfileConstraint`'s FKs to `Compound`/`ChemicalClass`/`Formulation`/`PropertyDefinition` already use string refs (`"core.Compound"` etc.), so no new cross-module imports are introduced there.
- **Repoint direct importers.** Change `from core.models.profiles import Profile` → `from core.models.profile import Profile` in `routine.py`, `location.py`, `reaction.py`; `from core.models.profiles import Profile, SkinProfile` → split across `profile`/`skin_profile` in `daily_checkin.py`. Update the block in `core/models/__init__.py`.
- **Verify no migration.** Run `makemigrations`; expect "No changes detected". If Django emits a migration, investigate before proceeding — it signals an unintended diff.

## Risks / Trade-offs

- **Missed direct importer.** A stray `core.models.profiles` import outside the five found would break at import time. Mitigation: grep the whole `backend/` tree for `models.profiles` before deleting the file, and run the test suite.
- **Circular import.** Splitting can surface latent import cycles. Low risk here because models use string FK references and only depend on `Profile`; mitigation is a full `python manage.py check` after the move.
