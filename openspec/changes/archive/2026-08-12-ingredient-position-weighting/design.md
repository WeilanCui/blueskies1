## Context

INCI rules require descending-concentration order above 1%; below 1% order is free. Position is therefore a coarse but real proxy: top-5 ≈ meaningful concentration, deep-list ≈ trace. `FormulationIngredient.position` is populated at parse time. Matching today returns booleans (`exists()`), discarding *which* ingredient matched and *where*.

## Goals / Non-Goals

**Goals:**
- Concentration-aware deltas for ingredient matches, with a formula simple enough to explain in one sentence.
- Never weaken safety signals (exclusions, warnings).
- Graceful behavior when positions are missing.

**Non-Goals:**
- True concentration estimation (percent modeling, 1%-line detection).
- Scaling property/raw-label/category matches (no position semantics).
- Re-ranking existing data migrations; this is compute-time only.

## Decisions

**1. Factor: linear decay by list fraction with floor.**
`factor = max(0.3, 1.0 − 0.7 × (position − 1) / max(total − 1, 1))` — position 1 → 1.0, last → 0.3, single-ingredient list → 1.0. Linear-with-floor over exponential decay: explainable ("earlier in the list = stronger effect"), no tuning constant beyond the floor, monotonic. The 0.3 floor keeps trace matches visible (a trace allergen penalty should shrink, not vanish).

**2. Best-position-wins for multi-ingredient matches.**
A chemical-class target matching ingredients at positions 3 and 30 uses position 3's factor (the strongest occurrence governs the effect).

**3. Applied to magnitudes only, and only for scoring kinds.**
`PENALIZE`/`BOOST`/`RECOMMEND` deltas: `round(base × factor)` with the existing `max(1, …)` guard on positive deltas. `EXCLUDE` stays absolute; `WARN`/`AVOID` are fully position-immune — both the caution text and, where AVOID carries one, the numeric delta stay unscaled, because a trace amount of something you must avoid is still worth avoiding. REFER unaffected (zero delta).

**4. Matching helpers return match detail, not booleans.**
`core/profiles/matching.py` functions return `MatchResult(matched: bool, best_position: int | None, total_ingredients: int | None)`. Both evaluators consume it; factor computed in one shared function `position_factor(result)`. Missing position/total → factor 1.0.

**5. `position_factor` exposed on impacts (nullable).**
Serializer adds it; UI may render "(low concentration)" when factor < 0.5. Additive.

## Risks / Trade-offs

- **Query shape change**: `exists()` → fetching matched positions (`values_list` min) adds per-check cost → mitigation: same N×M class; positions come from the already-joined ingredient rows; measured before/after in tests is out of scope, flagged for the perf follow-up.
- **Below-1% ordering is arbitrary** → factor pretends precision it lacks → mitigation: floor compresses deep-list differences (positions 30 vs 40 differ little); documented as proxy, not measurement.
- **Interaction with coverage stacking**: scaled boosts change `recommend-rule-coverage` magnitudes if both land → mitigation: composition is multiplicative on each rule's delta; specs of both changes stay consistent (coverage counts matches, not magnitudes).
