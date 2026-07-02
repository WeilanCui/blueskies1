## ADDED Requirements

### Requirement: Every match carries a defined data confidence

The system SHALL compute per-match data confidence as the fraction of the formulation's ingredients resolved to compounds (`parse_status=matched` with a compound), with gates: formulations with zero ingredients SHALL have confidence 0.0, and formulations with `enrichment_status=pending` SHALL be capped at 0.5. Confidence SHALL map to bands: high (≥ 0.8), medium (≥ 0.4), low (< 0.4).

#### Scenario: Fully resolved formulation

- **WHEN** all ingredients are matched to compounds and enrichment is complete
- **THEN** confidence is 1.0 and the band is high

#### Scenario: Partially resolved formulation

- **WHEN** 3 of 10 ingredients are resolved
- **THEN** confidence is 0.3 and the band is low

#### Scenario: No ingredients

- **WHEN** a formulation has no ingredient rows
- **THEN** confidence is 0.0

#### Scenario: Pending enrichment is capped

- **WHEN** every ingredient is resolved but enrichment_status is pending
- **THEN** confidence is at most 0.5

### Requirement: Confidence breaks ranking ties without altering scores

Ranked results SHALL order equal-final-score formulations by confidence band (high before medium before low) after the existing score ordering and before the name tie-breaker; the final score value itself SHALL NOT be modified by confidence.

#### Scenario: Unknown no longer outranks known at equal score

- **WHEN** an unparsed formulation and a fully resolved formulation both have final score 100
- **THEN** the resolved formulation ranks first

#### Scenario: Score still dominates

- **WHEN** a low-confidence formulation has score 90 and a high-confidence one has score 80
- **THEN** the score-90 formulation ranks first

### Requirement: Confidence is exposed and low confidence is visible in the UI

Match payloads SHALL include `data_confidence` (0–1, two decimals) and `confidence_band`; the "For You" list and score display SHALL show a limited-data indicator for low-band matches.

#### Scenario: API exposes confidence

- **WHEN** a client scores or ranks formulations
- **THEN** each match includes `data_confidence` and `confidence_band`

#### Scenario: UI flags thin data

- **WHEN** a ranked item's band is low
- **THEN** the item displays a "limited ingredient data" indicator at phone width without overflow
