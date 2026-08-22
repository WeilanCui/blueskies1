## 1. Create new model modules

- [x] 1.1 Create `backend/core/models/profile.py` with `ProfileVisibility` and `Profile` (verbatim from `profiles.py`).
- [x] 1.2 Create `backend/core/models/skin_profile.py` with `SkinType`, `FitzpatrickSkinType`, `PregnancyStatus`, and `SkinProfile`; add `from core.models.profile import Profile`.
- [x] 1.3 Create `backend/core/models/profile_constraint.py` with `ProfileConstraintKind`, `ConstraintEnforcement`, `ConstraintSeverity`, and `ProfileConstraint`; add `from core.models.profile import Profile`.
- [x] 1.4 Carry over only the imports each new module actually uses (e.g. `Q`/`timezone` only in `skin_profile.py`, `ValidationError`/validators where used).

## 2. Repoint imports

- [x] 2.1 Update `core/models/__init__.py`: replace the `from core.models.profiles import (...)` block with imports from `profile`, `skin_profile`, `profile_constraint`; keep `__all__` unchanged.
- [x] 2.2 Update direct importers: `routine.py`, `location.py`, `reaction.py` (`from core.models.profile import Profile`) and `daily_checkin.py` (`Profile` from `profile`, `SkinProfile` from `skin_profile`).
- [x] 2.3 Grep `backend/` for any remaining `models.profiles` references and repoint them.

## 3. Remove the old file

- [x] 3.1 Delete `backend/core/models/profiles.py`.

## 4. Verify

- [x] 4.1 Run `docker compose run --rm backend python manage.py check` — no errors, no import cycles.
- [x] 4.2 Run `docker compose run --rm backend python manage.py makemigrations` — expect "No changes detected".
- [x] 4.3 Run `docker compose run --rm backend python manage.py test core.tests.test_profile_constraints core.tests` — all pass.
