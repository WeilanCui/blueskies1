## ADDED Requirements

### Requirement: One profile model per module file

The profile domain models SHALL each live in their own module under `backend/core/models/`, named in snake_case after the primary model, in line with `.cursor/rules/django-model-files.mdc`. The aggregate `profiles.py` SHALL NOT exist after this change.

#### Scenario: Each profile model has a dedicated module

- **WHEN** a developer looks for `Profile`, `SkinProfile`, or `ProfileConstraint`
- **THEN** each is defined in `profile.py`, `skin_profile.py`, and `profile_constraint.py` respectively
- **AND** `backend/core/models/profiles.py` no longer exists

#### Scenario: Enums live with their consuming model

- **WHEN** a `TextChoices` enum is used by exactly one profile model
- **THEN** it is defined in that model's module (`ProfileVisibility` in `profile.py`; `SkinType`/`FitzpatrickSkinType`/`PregnancyStatus` in `skin_profile.py`; `ProfileConstraintKind`/`ConstraintEnforcement`/`ConstraintSeverity` in `profile_constraint.py`)

### Requirement: Public model imports remain stable

The split SHALL preserve the existing public import surface. `from core.models import <Name>` MUST continue to resolve every profile model and enum, and the database schema MUST be unchanged (no migration generated).

#### Scenario: Package-level imports unchanged

- **WHEN** code runs `from core.models import Profile, SkinProfile, ProfileConstraint`
- **THEN** the imports resolve from the new modules via `core/models/__init__.py` re-exports

#### Scenario: No schema drift

- **WHEN** `python manage.py makemigrations` runs after the split
- **THEN** no new migration is produced (file-only move, same app label and class names)
