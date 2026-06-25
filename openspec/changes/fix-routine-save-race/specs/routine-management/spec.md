## ADDED Requirements

### Requirement: Adding a product to a routine is concurrency-safe per profile

`RoutineAddProductSerializer.save()` SHALL serialize concurrent add-product operations for the same profile by acquiring a row-level lock on the owning `Profile` inside its atomic transaction, so that concurrent requests cannot create duplicate routines or collide on routine-item positions.

#### Scenario: Profile row is locked before reads

- **WHEN** `RoutineAddProductSerializer.save()` runs
- **THEN** it acquires a `SELECT … FOR UPDATE` lock on the owning `Profile` row before reading or creating the routine and before computing the next item position
- **AND** the lock is acquired within the existing `@transaction.atomic` block

#### Scenario: Concurrent adds do not duplicate routines or positions

- **WHEN** two add-product requests for the same profile and time-of-day run concurrently and no active routine yet exists
- **THEN** exactly one routine is created (the second request reuses it)
- **AND** no two routine items in that routine share the same position

#### Scenario: Single-request behavior unchanged

- **WHEN** a single add-product request is processed
- **THEN** the returned routine, the resulting `RoutineItem`, and the `created` flag are identical to the pre-change behavior
- **AND** re-adding the same product/formulation/raw name remains idempotent (no duplicate item)
