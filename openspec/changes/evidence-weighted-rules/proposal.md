## Why

The nightly literature pipeline ingests PubMed articles and links them to compounds (`CompoundLiterature`), and the `skinconcerns` app defines `ConcernEvidence` tying concern rules to that literature — but rule weights are static seed numbers. Evidence currently influences nothing: a rule backed by a systematic review scores identically to one backed by nothing. Modulating rule strength by evidence makes the literature pipeline load-bearing in recommendations and gives scores a provenance story.

## What Changes

- Concern-rule score deltas gain an **evidence multiplier** in [0.6, 1.3]: rules with no linked active evidence use 0.6 (dampened, still effective), rules with evidence scale up by evidence strength derived from `ConcernEvidence` rows (type and count), capped at 1.3.
- Delta becomes `round(weight × concern_confidence × evidence_multiplier)` for concern-sourced PENALIZE/BOOST/AVOID/RECOMMEND deltas. Profile-constraint deltas are untouched (user assertions are not literature claims).
- Concern-sourced impacts expose `evidence_count` and `evidence_multiplier`; the UI can render "backed by N sources" on reasons.
- An admin/management report (`manage.py evidence_gaps`) lists active rules with zero evidence, turning the gap into a curation worklist.

## Capabilities

### New Capabilities
- `evidence-weighted-scoring`: concern-rule deltas are modulated by linked evidence per a defined multiplier, exposed on impacts.

### Modified Capabilities
- `concern-rule-scoring`: the delta formula gains the evidence multiplier. (Delta against the `bridge-concern-rules` spec.)

## Impact

- `skinconcerns/scoring.py` (multiplier), a small `evidence_strength` helper reading `ConcernEvidence` (+ prefetch), serializer additions, one management command.
- Depends on: `bridge-concern-rules` (hard). Composes with `recommend-rule-coverage` and `ingredient-position-weighting` (multipliers stack on the same base delta).
- No model changes; `ConcernEvidence.evidence_type` enum already exists.
