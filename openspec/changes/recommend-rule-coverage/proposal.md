## Why

After `bridge-concern-rules`, RECOMMEND rules are recognized but inert. RECOMMEND is semantically different from BOOST: it says "this concern *wants* an ingredient like X," which supports coverage scoring — "this product contains 2 of the 3 actives recommended for your breakouts" — the core of a concerns-times-ingredients recommendation algorithm. Boost-style flat deltas cannot express "how well does this product serve the concern."

## What Changes

- Per scored formulation and per active user concern, compute **coverage**: of the concern's active RECOMMEND rules, how many match the formulation (`matched / total`).
- Coverage contributes to the score: each matched RECOMMEND rule adds `round(rule.weight × concern confidence)` (like BOOST), and the match gains a per-concern coverage summary (`concern`, `matched_rules`, `total_rules`, matched rule labels) in a new `coverage` section of the recommendation payload.
- Ranked catalog sorting is unchanged (still by final score); coverage is explanatory plus its score contribution.
- Frontend: "For You" list items and the score detail view render coverage lines ("Targets your breakouts: salicylic acid ✓, niacinamide ✗").

## Capabilities

### New Capabilities
- `concern-coverage-scoring`: RECOMMEND rules produce per-concern coverage (matched/total with labels) that contributes to the score and is exposed via the API and UI.

### Modified Capabilities
- `concern-rule-scoring`: RECOMMEND kind changes from informational-only to coverage-scored. (Delta against the `bridge-concern-rules` spec.)

## Impact

- `skinconcerns/scoring.py` (evaluator gains coverage aggregation), impact/evaluation dataclasses (coverage summaries), `core/serializers/recommendation.py`, recommendation frontend components.
- Depends on: `bridge-concern-rules`. No model or migration changes.
- Seed data already contains RECOMMEND rules (e.g. breakouts → acne actives) — feature is live on merge.
