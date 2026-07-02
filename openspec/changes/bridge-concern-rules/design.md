## Context

`ConcernRule` is a structural twin of `ProfileConstraint`: same target shapes (`compound` / `chemical_class` / `property_def` / raw text; plus `product_category`), a verb enum (`RuleKind`), an integer `weight`, and a human `rationale`. `SkinProfileConcern` carries a per-user `confidence` float. `ProfileConstraintEvaluator._matches_formulation` already implements the target-matching logic once. The matcher's output dataclasses (`ConstraintImpact`, `ConstraintEvaluation`, `RecommendationMatch`) are the API contract shipped by PR #41.

## Goals / Non-Goals

**Goals:**
- Selecting a concern measurably changes scores using seeded rules — no manual constraint entry.
- One combined, explainable evaluation: every impact says whether it came from a constraint or a concern rule, and why.
- Reuse the existing target-matching semantics; do not fork the matching logic.

**Non-Goals:**
- RECOMMEND coverage scoring (follow-up change `recommend-rule-coverage`).
- Evidence/literature modulation of weights (follow-up `evidence-weighted-rules`).
- Writing to `skinconcerns` tables, changing seeds, or UI for editing rules.
- Auto-deriving `SkinProfileConcern`s from intake text (already handled by `skinconcerns` services).

## Decisions

**1. Live second evaluator, not materialized ProfileConstraints.**
Materializing (syncing rules × concerns into derived `ProfileConstraint` rows) keeps the engine untouched but creates a shadow table that drifts: rule edits, concern deselection, and confidence updates all need sync hooks, and derived rows pollute the user's hand-entered constraint list in every UI that reads it. A `ConcernRuleEvaluator` reads live data, needs no lifecycle management, and makes provenance trivial (`source="concern"`). Cost: the matcher grows a second input path — acceptable, it is one composition point.

**2. Evaluator lives in `skinconcerns/scoring.py`, injected into the matcher by the view.**
`core` may not import from `skinconcerns` if `skinconcerns` already imports from `core` (it does: FKs to `core.Compound` etc. — but those are string references, and `skinconcerns.services` imports core models directly). Direction check: `skinconcerns` → `core` is the established dependency direction, so putting the evaluator in `skinconcerns` and having `core.profiles.recommendations` import it would invert nothing… but would make `core` depend on `skinconcerns`. Resolution: define a narrow protocol — `RecommendationMatcher` accepts an optional list of extra evaluators implementing `evaluate(profile, formulation) -> list[Impact]`; the concrete `ConcernRuleEvaluator` lives in `skinconcerns/scoring.py`, and the API view (which already knows both apps) injects it. Neither app gains a hard model-level dependency on the other; `core`'s engine stays framework-pure.

**3. Shared target matching via extraction.**
Extract `_matches_formulation`'s per-target checks into module-level functions (`matches_compound`, `matches_chemical_class`, `matches_property`, `matches_raw_label`) in `core/profiles/matching.py`; both evaluators call them. `ConcernRuleEvaluator` adds one new check, `matches_product_category` (case-insensitive equality on `formulation.product.category`).

**4. Scoring: `delta = round(rule.weight × concern_confidence)`, sign by kind.**
PENALIZE → −delta, BOOST → +max(1, delta), AVOID → warn impact and −delta (AVOID is stronger caution than PENALIZE but not a hard exclusion — hard exclusions remain the user's own constraints), REFER → 0 with informational impact, RECOMMEND → 0 with informational impact (until coverage change). Weights are seed-authored (default 10) so magnitudes are tunable in data, not code.

**5. Impact dataclass gains `source: str` (`"constraint"` | `"concern"`) and optional `concern_slug`.**
Existing constraint path sets `source="constraint"`; serializer exposes both fields. Additive, non-breaking for API consumers.

## Risks / Trade-offs

- **Double-penalty overlap**: a user with a hand-entered "avoid fragrance" constraint AND a concern rule penalizing fragrance gets both deltas → mitigation: acceptable for v1 (they express independent signals); flagged in docs; dedup heuristics deferred.
- **Query growth**: one prefetch of concerns→rules per run + category check per formulation → mitigation: rules resolved once per ranking run (like constraints already are); same complexity class.
- **AVOID vs EXCLUDE confusion**: seed authors may expect AVOID to hide products → mitigation: spec pins AVOID = strong caution, never exclusion; rationale strings surface in UI.
