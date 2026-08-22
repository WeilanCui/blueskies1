## Why

`RoutineAddProductSerializer.save()` (`backend/core/serializers/routine.py`) does read-then-write without a row-level lock, so concurrent "add product to routine" requests for the same profile race (cubic finding on PR #23, issue #24):

- `_get_or_create_routine` reads the active routine for a `(profile, time_of_day)` then creates one if absent. Two concurrent requests both read "none" and both create → **duplicate routines**.
- `next_position = max(position) + 1` is read then used for `RoutineItem.objects.create(...)`. Two concurrent requests pick the same position; `RoutineItem`'s existing `unique_routine_item_position` constraint then raises `IntegrityError` → **a 500 instead of a clean add**.

## What Changes

- Take a row-level lock on the owning `Profile` at the start of `save()` (inside the existing `@transaction.atomic`), via `Profile.objects.select_for_update().get(pk=...)`.
- This serializes all add-product operations for a given profile, so the get-or-create-routine and the max-position read-then-insert run without interleaving.
- No public API, request/response shape, or success-path behavior changes; only concurrent-collision behavior is fixed.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities

- `routine-management`: add-product-to-routine is now concurrency-safe per profile.

## Impact

- File: `backend/core/serializers/routine.py` (`RoutineAddProductSerializer.save()` only).
- Tests: add coverage asserting the profile row is locked under `select_for_update`; existing idempotency tests stay green.
- Requires the database transaction backend to support `SELECT … FOR UPDATE` (PostgreSQL — the project's DB). No migration.
- Stacked on PR #23 (the serializers split); targets that branch.
