## 1. Scaffold package

- [x] 1.1 Create `backend/core/serializers/` package directory.
- [x] 1.2 Delete the old `backend/core/serializers.py` once submodules exist.

## 2. Leaf + independent submodules (no intra-package deps)

- [x] 2.1 `compound.py` — CompoundAlias, CompoundIdentifier, CompoundStructure, ChemicalClass, ChemicalClassMembership, PropertyAssertion, Compound serializers.
- [x] 2.2 `auth.py` — AuthUser, Signup, Login serializers + `auth_user_payload`, `_unique_username_from_email`, `User = get_user_model()`.
- [x] 2.3 `contact.py` — ContactSubmissionSerializer.
- [x] 2.4 `location.py` — Location, WeatherSnapshot, ProfileLocation serializers.
- [x] 2.5 `product.py` — ProductSummarySerializer (shared base).
- [x] 2.6 `catalog.py` — `CATALOG_SOURCE_PREFIX`, `catalog_slug`, `serialize_catalog_product`.
- [x] 2.7 `intake.py` — IntakeSerializer + `intake_payload`.

## 3. Dependent submodules (import from product/formulation/routine)

- [x] 3.1 `formulation.py` — FormulationIngredient, Formulation, FormulationSubmit serializers (imports ProductSummarySerializer from `core.serializers.product`).
- [x] 3.2 `routine.py` — RoutineItem, Routine, RoutineAddProduct serializers + `infer_routine_step_from_product` (imports ProductSummarySerializer, FormulationSerializer).
- [x] 3.3 `daily_checkin.py` — DailyProductUse, DailyCheckIn, TodayCheckIn serializers (imports ProductSummary, Formulation, RoutineItem serializers).
- [x] 3.4 `reaction.py` — ReactionEventSerializer (imports ProductSummary, Formulation serializers).

## 4. Re-export

- [x] 4.1 `__init__.py` re-exports every public name from submodules; alphabetized `__all__` matching `core/models/__init__.py` style. `_unique_username_from_email` stays private.

## 5. Verify

- [x] 5.1 Importable name-set from `core.serializers` identical before/after (every name in `views.py` + test imports resolves).
- [x] 5.2 `manage.py check` clean.
- [x] 5.3 `manage.py makemigrations --check --dry-run` reports "No changes detected".
- [x] 5.4 Existing test suite passes (`pytest`).
- [x] 5.5 `openspec validate split-serializers-package --strict` passes.
