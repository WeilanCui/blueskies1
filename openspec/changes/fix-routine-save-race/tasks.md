## 1. Fix

- [x] 1.1 In `RoutineAddProductSerializer.save()` (`backend/core/serializers/routine.py`), make the first statement inside the atomic block re-fetch the profile under a row lock: `profile = Profile.objects.select_for_update().get(pk=self.context["profile"].pk)`. Use this locked `profile` for the rest of the method (`_get_or_create_routine`, item creation). `Profile` is already imported.

## 2. Tests

- [x] 2.1 Add a test asserting `save()` fetches the profile via `select_for_update` (e.g. patch/spy on `Profile.objects.select_for_update` and assert it is called, or assert the query uses `FOR UPDATE`).
- [x] 2.2 Add/confirm a test that calling `save()` twice for the same product is idempotent (single item) and that adding to an existing active routine does not create a second routine.

## 3. Verify

- [x] 3.1 Full backend test suite passes (`pytest`) against PostgreSQL.
- [x] 3.2 `manage.py check` clean; `manage.py makemigrations --check --dry-run` reports "No changes detected" (no schema change).
- [x] 3.3 `openspec validate fix-routine-save-race --strict` passes.
