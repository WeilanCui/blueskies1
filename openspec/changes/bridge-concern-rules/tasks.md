## 1. Shared matching extraction

- [ ] 1.1 Extract per-target checks from `ProfileConstraintEvaluator._matches_formulation` into `core/profiles/matching.py` (`matches_compound`, `matches_chemical_class`, `matches_property`, `matches_raw_label`); constraint evaluator delegates to them (behavior identical, existing tests green)
- [ ] 1.2 Add `matches_product_category(formulation, category)` (case-insensitive)

## 2. Impact model + evaluator protocol

- [ ] 2.1 Add `source` (default `"constraint"`) and optional `concern_slug` to the impact dataclass; constraint path populates `source="constraint"`
- [ ] 2.2 `RecommendationMatcher` accepts optional `extra_evaluators: list` with `evaluate(profile, formulation, ...) -> list[Impact]`; impacts merged into the evaluation groups by enforcement kind

## 3. ConcernRuleEvaluator

- [ ] 3.1 Create `skinconcerns/scoring.py` with `ConcernRuleEvaluator`: resolve active `SkinProfileConcern`s → active `ConcernRule`s once per run (prefetch), match per formulation via `core/profiles/matching.py`
- [ ] 3.2 Map kinds: PENALIZE→−delta, BOOST→+max(1,delta), AVOID→warning+−delta, REFER→informational 0, RECOMMEND→informational 0; `delta = round(weight × concern_confidence)`
- [ ] 3.3 Inject the evaluator in `RecommendationViewSet` (both actions)

## 4. API serialization

- [ ] 4.1 Impact serializer gains `source` and `concern` (slug, nullable); update frontend `ConstraintImpact` type additively

## 5. Tests

- [ ] 5.1 Matching-extraction parity: existing constraint tests pass unchanged
- [ ] 5.2 Evaluator unit tests: each kind, confidence scaling, inactive link/rule ignored, product-category targeting
- [ ] 5.3 API tests: mixed constraint+concern impacts with correct `source`/`concern`; no-concern profile identical to today
- [ ] 5.4 Full suite green

## 6. Docs

- [ ] 6.1 CLAUDE.md/README: concern rules now feed scoring; AVOID ≠ exclusion
