## 1. Evaluator coverage

- [ ] 1.1 Add `CoverageSummary` dataclass (`concern_slug`, `concern_label`, `matched_labels`, `unmatched_labels`, `matched`, `total`)
- [ ] 1.2 `ConcernRuleEvaluator` aggregates RECOMMEND rules per concern: matched → boost impact (`max(1, round(weight × confidence))`, `source="concern"`) + label into summary; unmatched → label only; omit zero-total concerns
- [ ] 1.3 Evaluation/match structures gain `coverage: list[CoverageSummary]`; matcher passes it through

## 2. API

- [ ] 2.1 `RecommendationMatchSerializer` gains `coverage` array (`concern`, `concern_label`, `matched`, `total`, `matched_rules`)
- [ ] 2.2 Frontend types updated additively

## 3. Frontend

- [ ] 3.1 "For You" list items render one coverage line per concern (matched actives), mobile-first
- [ ] 3.2 Score detail (scan badge context) shows coverage breakdown incl. unmatched labels

## 4. Tests

- [ ] 4.1 Coverage math: partial/zero/full match, omission of no-RECOMMEND concerns, denominator correctness
- [ ] 4.2 Ranking: product matching a RECOMMEND rule outranks an identical inert product
- [ ] 4.3 API shape test for `coverage`; existing tests green

## 5. Docs

- [ ] 5.1 Update recommendation endpoint docs with `coverage`
