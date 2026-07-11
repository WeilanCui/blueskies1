## ADDED Requirements

### Requirement: Concern-rule deltas are modulated by rule-scoped evidence

The system SHALL compute an evidence multiplier per concern rule as `clamp(0.6 + Σ type_weight per distinct active evidence reference, 0.6, 1.3)` using type weights (clinical 0.15; regulatory and safety 0.12; public_guidance 0.08; rule and definition 0.05), counting only `ConcernEvidence` rows scoped to that rule, and SHALL apply it multiplicatively to concern-sourced score deltas.

#### Scenario: Zero-evidence rule is dampened

- **WHEN** an active concern rule has no rule-scoped evidence
- **THEN** its score delta uses multiplier 0.6

#### Scenario: Clinical evidence strengthens a rule

- **WHEN** a rule gains two distinct clinical evidence references
- **THEN** its multiplier is 0.9 and its delta grows accordingly

#### Scenario: Multiplier is capped

- **WHEN** a rule accumulates evidence whose type weights sum past the cap
- **THEN** the multiplier is 1.3

#### Scenario: Concern-level evidence does not transfer

- **WHEN** evidence rows link to the concern but not to the rule
- **THEN** the rule's multiplier remains 0.6

#### Scenario: Duplicate citations count once

- **WHEN** two evidence rows on the same rule cite the same literature reference
- **THEN** the reference contributes its type weight once

#### Scenario: Profile constraints unaffected

- **WHEN** a profile constraint scores a formulation
- **THEN** its delta has no evidence multiplier applied

### Requirement: Evidence influence is exposed on impacts

Concern-sourced impacts SHALL include `evidence_count` (distinct references) and `evidence_multiplier`, enabling clients to render source-backed reasons.

#### Scenario: API exposes evidence fields

- **WHEN** a concern rule with evidence matches a formulation
- **THEN** the impact includes its `evidence_count` and `evidence_multiplier`

### Requirement: Evidence gaps are reportable

A management command SHALL list all active concern rules with zero rule-scoped evidence, grouped by concern.

#### Scenario: Curation worklist

- **WHEN** an operator runs the evidence-gaps command
- **THEN** every active zero-evidence rule is listed with its concern slug and rule key
