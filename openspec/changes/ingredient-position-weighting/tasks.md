## 1. Matching detail

- [ ] 1.1 `core/profiles/matching.py`: compound/class helpers return `MatchResult(matched, best_position, total_ingredients)` instead of bool (min position via aggregate; total from ingredient count)
- [ ] 1.2 Shared `position_factor(result) -> float` implementing the linear-decay-with-floor formula; None inputs → 1.0

## 2. Scoring integration

- [ ] 2.1 Constraint evaluator: scale PENALIZE/BOOST deltas for compound/class targets; EXCLUDE/WARN emission untouched; other targets factor=None
- [ ] 2.2 Concern-rule evaluator (if `bridge-concern-rules` landed): same scaling for PENALIZE/BOOST/RECOMMEND, AVOID delta scaled but warning kept; guard so this change also applies cleanly if it lands first (constraints only)
- [ ] 2.3 Impact dataclass + serializer gain nullable `position_factor`

## 3. Tests

- [ ] 3.1 Factor math: position 1 → 1.0, last → 0.3, single-ingredient → 1.0, missing data → 1.0, best-position-wins
- [ ] 3.2 Scoring: trace vs headline penalty ordering; EXCLUDE positional immunity; non-ingredient targets null factor + unchanged delta
- [ ] 3.3 API shape includes `position_factor`; full suite green

## 4. Docs

- [ ] 4.1 Document the proxy nature of INCI position and the formula in CLAUDE.md/README
