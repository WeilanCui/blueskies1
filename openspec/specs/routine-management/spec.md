# routine-management Specification

## Purpose
TBD - created by archiving change dedup-routine-validation. Update Purpose after archive.
## Requirements
### Requirement: Routine product/formulation validation is centralized

Product/formulation resolution and validation for routine items SHALL be defined once and reused by both `RoutineItemSerializer` and `RoutineAddProductSerializer`, so the two paths cannot diverge. The externally observable validation behavior SHALL be unchanged.

#### Scenario: Single shared resolver

- **WHEN** reading `backend/core/serializers/routine.py`
- **THEN** there is one shared helper resolving `(product, formulation, raw_product_name)`
- **AND** both `RoutineItemSerializer.validate` and `RoutineAddProductSerializer.validate` call it instead of duplicating the resolution block

#### Scenario: Validation errors preserved

- **WHEN** a routine item or add-product request supplies an unknown `product_id`
- **THEN** validation fails with `{"product_id": "Product not found."}`
- **AND** an unknown `formulation_id` fails with `{"formulation_id": "Formulation not found."}`
- **AND** a `formulation_id` whose formulation belongs to a different product than the supplied `product_id` fails with `{"formulation_id": "Formulation must belong to product."}`
- **AND** supplying none of product/formulation/raw_product_name fails with "Routine item needs a product, formulation, or raw_product_name."

#### Scenario: Success path unchanged

- **WHEN** a valid product, formulation, or raw_product_name is supplied
- **THEN** the resolved product/formulation/raw_product_name written to validated data are identical to the pre-refactor behavior (including `raw_product_name` stripping and inferring the product from a formulation when only `formulation_id` is given)

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

