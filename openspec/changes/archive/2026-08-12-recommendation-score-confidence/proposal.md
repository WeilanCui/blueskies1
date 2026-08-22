## Why

The engine scores what it can see — and silently sees nothing when data is missing. A formulation with an unparsed INCI list, unresolved ingredients (`parse_status` unmatched/ambiguous), or pending enrichment matches no constraints and keeps the base score of 100, ranking *above* well-understood products with minor penalties. Unknown is currently indistinguishable from good, which quietly rewards the worst-documented products.

## What Changes

- Each recommendation match gains a **data confidence** value in [0, 1] derived from the formulation's ingredient knowledge: fraction of ingredients resolved to compounds, degraded when the formulation has no ingredients at all or enrichment is pending.
- Ranked catalog ordering incorporates confidence as a tie-breaker tier: among equal final scores, higher-confidence products rank first; additionally, zero-ingredient formulations rank below any scored formulation of equal score.
- The API exposes `data_confidence` (and a coarse `confidence_band`: high/medium/low) per match; the score endpoint includes it too.
- Frontend: "For You" items and the score badge context show a low-confidence marker ("limited ingredient data") when the band is low.
- Final scores are NOT multiplied by confidence — the score keeps meaning "fit given what we know"; confidence says how much we know.

## Capabilities

### New Capabilities
- `score-data-confidence`: every match carries a defined data-confidence measure that affects ranking order (as a tier/tie-breaker) and is exposed for display.

### Modified Capabilities
- `recommendation-api`: match payloads gain `data_confidence` and `confidence_band`; ranked ordering adds the confidence tie-breaker. (Delta on the `expose-recommendations` spec.)

## Impact

- `core/profiles/recommendations.py` (confidence computation + sort key), serializers, frontend list/badge components.
- No model changes — `parse_status`, `enrichment_status`, ingredient counts all exist.
- Independent of the concern-rule changes; composes with them (confidence is orthogonal to signal source).
