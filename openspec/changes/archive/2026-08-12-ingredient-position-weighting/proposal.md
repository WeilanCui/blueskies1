## Why

`FormulationIngredient.position` encodes INCI list order — the industry-standard concentration proxy — but the engine ignores it entirely: retinol as the 2nd ingredient scores identically to retinol as the 40th (trace). This makes both penalties (allergen present in trace amounts) and boosts/coverage (active present in trace amounts) misleadingly flat.

## What Changes

- Ingredient-targeted matches (compound and chemical-class targets, from both profile constraints and concern rules) gain a **position factor** in [0.3, 1.0]: 1.0 for top-of-list ingredients, decaying toward 0.3 deep in the list, floor so nothing vanishes.
- Score deltas become `round(base_delta × position_factor)` for ingredient-targeted PENALIZE/BOOST/RECOMMEND matches. Hard exclusions (EXCLUDE), warnings (WARN/AVOID), REFER, and non-ingredient targets (property, raw label, product category, formulation-specific) are NOT scaled — safety signals must not fade with concentration.
- Impact payloads gain `position_factor` (nullable) so the UI can explain "low concentration" when relevant.

## Capabilities

### New Capabilities
- `position-weighted-scoring`: INCI position modulates ingredient-match score deltas with a defined decay and floor, exposed for explanation.

### Modified Capabilities
<!-- None: constraint and concern-rule scoring formulas are parameterized, not re-specified; this capability defines the factor and where it applies. -->

## Impact

- `core/profiles/matching.py` (match helpers return matched positions), `constraints.py` + `skinconcerns/scoring.py` (apply factor), impact dataclass + serializer (`position_factor`).
- No model changes; `position` already stored. Independent of other proposed changes but composes with them (applies wherever ingredient matches score).
- Risk of unparsed lists: formulations whose ingredients lack positions fall back to factor 1.0 (current behavior).
