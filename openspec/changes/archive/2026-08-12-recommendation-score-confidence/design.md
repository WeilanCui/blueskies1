## Context

`FormulationIngredient.parse_status` ∈ {matched, unmatched, ambiguous}; `Formulation.enrichment_status` ∈ {pending, partial, complete, needs_review}. The matcher's base score (100) means "no negative signals found" — vacuously true when there is nothing to inspect. Ranking sorts `(excluded, -final_score, name, id)`.

## Goals / Non-Goals

**Goals:**
- A per-match confidence number with a simple, defensible definition.
- Unknown products stop outranking well-understood ones at equal score.
- Users can see when a score rests on thin data.

**Non-Goals:**
- Bayesian/probabilistic scoring, confidence intervals on the score value.
- Multiplying or shrinking scores by confidence (changes score semantics; hides the distinction the UI should show).
- Backfilling parse quality; ingestion improvements are separate work.

## Decisions

**1. Confidence = resolved-ingredient fraction with structural gates.**
`confidence = resolved / total` where resolved = ingredients with `parse_status=matched` and a non-null compound. Gates: no ingredients at all → 0.0; `enrichment_status=pending` → capped at 0.5. Bands: high ≥ 0.8, medium ≥ 0.4, low otherwise. One intuitive quantity ("we understand 83% of this label"); enrichment gate encodes "we haven't finished looking."

**2. Ranking: confidence is a sort tier between score and name.**
New key: `(excluded, -final_score, confidence_tier, name, id)` where `confidence_tier` orders high < medium < low (i.e. high first). Tier, not raw value, so near-identical fractions don't produce unstable orderings; score remains the dominant signal. Alternative — subtracting a confidence penalty from the score — rejected: conflates fit with knowledge and breaks the score's explainability (every point currently traces to an impact).

**3. Exposed as `data_confidence` (float, 2dp) + `confidence_band` (enum).**
Band drives UI; float supports future tuning and sorting transparency.

**4. Computed in `RecommendationMatcher` per formulation, from prefetched ingredients.**
No extra queries when the ranking queryset already prefetches ingredients (it does, for matching). Single helper `data_confidence(formulation) -> float` unit-testable in isolation.

## Risks / Trade-offs

- **Punishes new/indie products with poor label data** → mitigation: tier only breaks ties; a great score still ranks; UI wording is "limited data," not "bad product."
- **Threshold arbitrariness (0.8/0.4)** → mitigation: constants in one place, spec'd as defaults, env-tunable later if needed.
- **Score-100 crowding**: many unknown products share score 100, so the tie-breaker does real work there — by design; that is exactly the failure mode being fixed.
