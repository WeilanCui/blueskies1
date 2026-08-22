## MODIFIED Requirements

### Requirement: Concern rules participate in formulation scoring

The system SHALL evaluate the active `ConcernRule`s of every concern actively linked to the user's skin profile (`SkinProfileConcern`) against each scored formulation, using the same target-matching semantics as profile constraints (compound, chemical class, property, raw text) plus product category, and SHALL fold matching rules into the recommendation score with delta `round(rule.weight × concern confidence × evidence multiplier)` as defined by `evidence-weighted-scoring`.

#### Scenario: Penalize rule lowers the score

- **WHEN** a user has an active concern whose PENALIZE rule targets a chemical class present in a formulation's resolved ingredients
- **THEN** the formulation's final score is reduced by `round(rule.weight × concern confidence × evidence multiplier)` and the match lists a penalty impact carrying the rule's rationale

#### Scenario: Boost rule raises the score

- **WHEN** an active concern has a BOOST rule matching the formulation
- **THEN** the final score increases by at least 1 and the impact appears in the boosts group

#### Scenario: Avoid rule warns and penalizes without excluding

- **WHEN** an active concern has an AVOID rule matching the formulation
- **THEN** the match gains a warning impact and a negative score delta, but `excluded` remains false unless a profile constraint independently excludes it

#### Scenario: Refer rule is informational only

- **WHEN** an active concern has a REFER rule matching the formulation
- **THEN** the impact is reported with zero score delta

#### Scenario: Inactive links and rules are ignored

- **WHEN** a `SkinProfileConcern` link or a `ConcernRule` is inactive
- **THEN** it contributes no impacts

#### Scenario: Confidence scales the effect

- **WHEN** two users select the same concern with confidences 1.0 and 0.5
- **THEN** the same matching rule produces half the score delta (rounded) for the lower-confidence user

#### Scenario: No concerns selected

- **WHEN** the user's profile has no active concern links
- **THEN** scoring behaves exactly as constraint-only scoring does today
