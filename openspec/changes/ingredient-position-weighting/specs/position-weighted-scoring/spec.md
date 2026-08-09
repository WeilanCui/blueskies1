## ADDED Requirements

### Requirement: Ingredient matches carry a position factor

For matches targeting a compound or chemical class, the system SHALL compute a position factor `max(0.3, 1.0 − 0.7 × (position − 1) / max(total − 1, 1))` from the best (lowest) matching ingredient position and the formulation's ingredient count; matches with unknown position or total SHALL use factor 1.0.

#### Scenario: Top-of-list ingredient scores fully

- **WHEN** the matched ingredient is at position 1
- **THEN** the position factor is 1.0

#### Scenario: Last ingredient hits the floor

- **WHEN** the matched ingredient is the last of a multi-ingredient list
- **THEN** the position factor is 0.3

#### Scenario: Best occurrence governs

- **WHEN** a chemical-class target matches ingredients at positions 3 and 30
- **THEN** the factor derives from position 3

#### Scenario: Missing position data is neutral

- **WHEN** matched ingredients lack position or the formulation lacks a total count
- **THEN** the factor is 1.0 and scoring equals current behavior

### Requirement: Position factor scales score deltas but not safety signals


PENALIZE, BOOST, and RECOMMEND deltas from ingredient-targeted matches SHALL become `round(base_delta × factor)` (positive deltas keep the minimum of 1). EXCLUDE decisions and AVOID matches (both the warning and its numeric delta) SHALL be position-immune — safety signals must not fade with concentration; property, raw-label, product-category, and formulation-specific targets SHALL NOT be scaled.

#### Scenario: Trace allergen penalizes less than headline allergen

- **WHEN** the same PENALIZE constraint matches an ingredient at position 2 in one formulation and near the end of another (same length lists)
- **THEN** the first formulation receives a strictly larger penalty

#### Scenario: Exclusion ignores position

- **WHEN** an EXCLUDE constraint matches an ingredient at the last position
- **THEN** the formulation is excluded exactly as if the ingredient were first

#### Scenario: Non-ingredient targets unscaled

- **WHEN** a raw-label or property-targeted match scores
- **THEN** its delta is identical to current behavior and its `position_factor` is null

### Requirement: Position factor is exposed for explanation

Serialized impacts SHALL include a nullable `position_factor`; ingredient-targeted matches carry the computed value.

#### Scenario: API exposes the factor

- **WHEN** a client scores a formulation with an ingredient-targeted match
- **THEN** the corresponding impact includes its `position_factor`
