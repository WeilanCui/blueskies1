## ADDED Requirements

### Requirement: Match payloads include confidence fields

Serialized recommendation matches (score and ranked list) SHALL additively include `data_confidence` (float, 0–1) and `confidence_band` (`high` | `medium` | `low`); ranked ordering SHALL apply the confidence tie-breaker defined by `score-data-confidence`. All previously specified fields and behaviors are unchanged.

#### Scenario: Both endpoints expose confidence

- **WHEN** a client calls the score endpoint or the ranked list endpoint
- **THEN** every match object includes `data_confidence` and `confidence_band`
