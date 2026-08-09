## 1. Matching detail

- [x] 1.1 `core/profiles/matching.py`: compound/class helpers return `MatchResult(matched, best_position, total_ingredients)` instead of bool (min position via aggregate; total from ingredient count)
- [x] 1.2 Shared `position_factor(result) -> float` implementing the linear-decay-with-floor formula; None inputs → 1.0

## 2. Scoring integration

- [x] 2.1 Constraint evaluator: scale PENALIZE/BOOST deltas for compound/class targets; EXCLUDE/WARN emission untouched; other targets factor=None
- [x] 2.2 Concern-rule evaluator (if `bridge-concern-rules` landed): same scaling for PENALIZE/BOOST/RECOMMEND, AVOID fully position-immune (warning and delta both unscaled); guard so this change also applies cleanly if it lands first (constraints only)
- [x] 2.3 Impact dataclass + serializer gain nullable `position_factor`

## 3. Tests

- [x] 3.1 Factor math: position 1 → 1.0, last → 0.3, single-ingredient → 1.0, missing data → 1.0, best-position-wins
- [x] 3.2 Scoring: trace vs headline penalty ordering; EXCLUDE positional immunity; non-ingredient targets null factor + unchanged delta
- [x] 3.3 API shape includes `position_factor`; full suite green

## 4. Docs

- [x] 4.1 Document the proxy nature of INCI position and the formula in CLAUDE.md/README
