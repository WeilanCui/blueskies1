## ADDED Requirements

### Requirement: Impact payloads carry a source discriminator

Serialized recommendation impacts SHALL include a `source` field valued `constraint` or `concern`, and concern-sourced impacts SHALL include the originating concern's slug, so clients can render the two signal families distinctly. Existing fields are unchanged.

#### Scenario: Constraint impacts unchanged plus source

- **WHEN** a client scores a formulation matching only profile constraints
- **THEN** every impact has `source: "constraint"` and all previously specified fields

#### Scenario: Concern impacts identified

- **WHEN** a scored formulation matches a concern rule
- **THEN** that impact has `source: "concern"` and a `concern` field with the concern slug
