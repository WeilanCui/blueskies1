## Why

PR #38 shipped a full `skinconcerns` app — 21 seeded `SkinConcern`s, per-concern `ConcernRule`s (AVOID/PENALIZE/BOOST/RECOMMEND/REFER with weights and rationale), and `SkinProfileConcern` linking users to concerns with confidence — but nothing consumes it: `RecommendationMatcher` only reads hand-entered `ProfileConstraint`s. A user who selects "breakouts" gets zero scoring effect from the acne rules the seed data already defines. This change wires concern rules into the engine so selecting a concern changes recommendations.

## What Changes

- Add a `ConcernRuleEvaluator` in `core/profiles/` (or `skinconcerns/`, decided in design) that, given a profile, resolves the user's active `SkinProfileConcern`s → their concerns' active `ConcernRule`s → matches each rule against a formulation using the same target semantics as `ProfileConstraintEvaluator` (compound / chemical class / property / raw text, plus product category).
- Extend `RecommendationMatcher` to combine constraint impacts and concern-rule impacts into one evaluation: AVOID → warn-level impact, PENALIZE → negative delta, BOOST → positive delta, each scaled by `rule.weight × profile_concern.confidence`. REFER surfaces as an informational impact (no score change). RECOMMEND is recognized but its scoring semantics are delivered by the follow-up `recommend-rule-coverage` change (here it produces an informational match only).
- Recommendation API responses include concern-sourced impacts with rule rationale in `reason`, distinguishable from constraint-sourced impacts (`source: "concern"` vs `"constraint"`).
- No changes to `skinconcerns` models; read-only consumption.

## Capabilities

### New Capabilities
- `concern-rule-scoring`: concern rules attached to a user's selected skin concerns participate in formulation scoring and appear as explainable impacts.

### Modified Capabilities
- `recommendation-api`: match responses gain a `source` discriminator on impacts and may include concern-sourced impacts. (Delta on the spec added by `expose-recommendations`.)

## Impact

- `core/profiles/` — new evaluator module + `RecommendationMatcher` composition; `constraints.py` untouched.
- `core/serializers/recommendation.py` — impact serializer gains `source` (and `concern` slug when concern-sourced).
- New tests: rule-target matching parity, weight×confidence scaling, REFER informational, API shape.
- Depends on: `expose-recommendations` (PR #41) merged. Blocks: `recommend-rule-coverage`, `evidence-weighted-rules`.
- Perf: adds one query for profile concerns + rules per ranking run (prefetched), plus per-formulation target checks identical in shape to existing constraint checks — same N×M class as today.
