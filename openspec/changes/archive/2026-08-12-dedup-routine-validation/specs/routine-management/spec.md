## ADDED Requirements

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
