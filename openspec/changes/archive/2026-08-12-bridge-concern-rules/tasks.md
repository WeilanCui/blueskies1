## 1. Shared matching extraction

- [x] 1.1 Extract per-target checks from `ProfileConstraintEvaluator._matches_formulation` into `core/profiles/matching.py` (`matches_compound`, `matches_chemical_class`, `matches_property`, `matches_raw_label`); constraint evaluator delegates to them (behavior identical, existing tests green)
- [x] 1.2 Add `matches_product_category(formulation, category)` (case-insensitive)

## 2. Impact model + evaluator protocol

- [x] 2.1 Add `source` (default `"constraint"`) and optional `concern_slug` to the impact dataclass; constraint path populates `source="constraint"`
- [x] 2.2 `RecommendationMatcher` accepts optional `extra_evaluators: list` with `evaluate(profile, formulation, ...) -> list[Impact]`; impacts merged into the evaluation groups by enforcement kind

## 3. ConcernRuleEvaluator

- [x] 3.1 Create `skinconcerns/scoring.py` with `ConcernRuleEvaluator`: resolve active `SkinProfileConcern`s → active `ConcernRule`s once per run (prefetch), match per formulation via `core/profiles/matching.py`
- [x] 3.2 Map kinds: PENALIZE→−delta, BOOST→+max(1,delta), AVOID→warning+−delta, REFER→informational 0, RECOMMEND→informational 0; `delta = round(weight × concern_confidence)`
- [x] 3.3 Inject the evaluator in `RecommendationViewSet` (both actions)

## 4. API serialization

- [x] 4.1 Impact serializer gains `source` and `concern` (slug, nullable); update frontend `ConstraintImpact` type additively

## 5. Tests

- [x] 5.1 Matching-extraction parity: existing constraint tests pass unchanged
- [x] 5.2 Evaluator unit tests: each kind, confidence scaling, inactive link/rule ignored, product-category targeting
- [x] 5.3 API tests: mixed constraint+concern impacts with correct `source`/`concern`; no-concern profile identical to today
- [x] 5.4 Full suite green (238 tests; sole failure is the unrelated pre-existing core.tests.test_locations weather-snapshot test)

## 6. Docs

- [x] 6.1 CLAUDE.md/README: concern rules now feed scoring; AVOID ≠ exclusion
