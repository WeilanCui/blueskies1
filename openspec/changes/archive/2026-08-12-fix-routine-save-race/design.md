## Context

`RoutineAddProductSerializer.save()` is already wrapped in `@transaction.atomic`, but atomicity alone does not prevent the race: two concurrent transactions can each read a snapshot in which the target routine / max position does not yet exist, then both write. The `RoutineItem` model already has `UniqueConstraint(fields=["routine", "position"], name="unique_routine_item_position")`, so the position collision surfaces as an `IntegrityError` rather than silent corruption — but that is still a user-facing 500. There is no uniqueness guard on routines, so the duplicate-routine path corrupts silently.

## Goals / Non-Goals

**Goals:**
- Concurrent add-product requests for the same profile cannot create duplicate routines or collide on item position.
- Success-path behavior (return value, `self.item`, `self.created`, idempotent re-add via `_find_existing_item`) is unchanged.

**Non-Goals:**
- No change to single-request behavior or API shape.
- No new migration / no schema change.
- Not fixing the unrelated cubic findings #25 (dedup) / #26 (`.count()`).

## Decisions

### Lock the Profile row, not the Routine row

`save()` re-fetches the profile with `Profile.objects.select_for_update().get(pk=self.context["profile"].pk)` as the first statement inside the atomic block, and uses that locked instance for the rest of the method.

- A `select_for_update` on the *routine* row cannot prevent the duplicate-**routine** race, because the row does not exist yet when both transactions check — there is nothing to lock. Locking the parent `Profile` row gives a stable per-profile mutex that exists in all cases.
- Granularity: one profile = one concurrent add-product critical section. Add-product is a low-frequency, user-initiated action, so per-profile serialization is acceptable and far cheaper than a global lock.
- The lock is released at transaction commit/rollback (end of the `@transaction.atomic` block), so it is held only for the duration of the operation.

### Keep the lock acquisition explicit and early

The lock is the first DB access in `save()`, before `_get_or_create_routine`, `_find_existing_item`, and the position computation, so every subsequent read is serialized behind it.

## Risks / Trade-offs

- **Backend support:** `select_for_update()` requires a transactional DB with row locking (PostgreSQL — used here). On SQLite it is a no-op; tests run against PostgreSQL so behavior is verified there.
- **Lock contention:** two rapid add-product requests for the same profile now serialize instead of racing. Acceptable for a human-driven action.
- **Test determinism:** a true thread-level race test is flaky. The spec verifies (a) the profile is fetched under `select_for_update` (deterministic, mock/assertion based) and (b) existing idempotency behavior is preserved.
