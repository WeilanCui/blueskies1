## ADDED Requirements

### Requirement: Per-concern RECOMMEND coverage is computed for every match

For each scored formulation and each of the user's active concerns having at least one active RECOMMEND rule, the system SHALL report how many of those rules match the formulation (`matched` of `total`), with the labels of matched and unmatched rules.

#### Scenario: Partial coverage reported

- **WHEN** a concern has three active RECOMMEND rules and the formulation matches two
- **THEN** the match's coverage lists that concern with `matched=2`, `total=3`, and the two matched labels

#### Scenario: Concern without RECOMMEND rules omitted

- **WHEN** an active concern has no active RECOMMEND rules
- **THEN** no coverage entry is emitted for it

#### Scenario: Coverage denominator includes unmatched rules

- **WHEN** none of a concern's RECOMMEND rules match
- **THEN** the coverage entry reports `matched=0` with the full `total`

### Requirement: Matched RECOMMEND rules contribute positive score

Each matched RECOMMEND rule SHALL add `max(1, round(rule.weight × concern confidence))` to the formulation's score as a boost impact with `source="concern"`; unmatched RECOMMEND rules SHALL NOT reduce the score.

#### Scenario: Product serving a concern outranks an inert one

- **WHEN** two otherwise-identical formulations are ranked and only one matches a RECOMMEND rule for the user's concern
- **THEN** the matching formulation receives a higher final score

#### Scenario: Absence is not penalized

- **WHEN** a formulation matches no RECOMMEND rules
- **THEN** it receives no negative delta from RECOMMEND rules

### Requirement: Coverage is exposed via API and rendered in the UI

The recommendation match payload SHALL include a `coverage` array (`concern`, `concern_label`, `matched`, `total`, `matched_rules` labels), and the "For You" list and score detail SHALL render a coverage line per concern.

#### Scenario: API payload carries coverage

- **WHEN** a client scores or ranks formulations for a user with active concerns
- **THEN** each match includes the `coverage` array as specified

#### Scenario: UI shows why a product is recommended

- **WHEN** a ranked item has coverage for the user's concern
- **THEN** the "For You" item displays the concern with its matched-active summary at phone width without overflow
