## Context

`ConcernEvidence` links a `SkinConcern` (and optionally a specific `ConcernRule`) to a `CompoundLiterature` reference with an `evidence_type` ∈ {definition, rule, regulatory, safety, public_guidance, clinical}. The nightly Celery pipeline keeps `CompoundLiterature` growing. `bridge-concern-rules` establishes the delta formula `round(weight × concern_confidence)`; this change multiplies in evidence strength.

## Goals / Non-Goals

**Goals:**
- Rules with real backing hit harder than bare assertions, per a formula explainable as "backed by N sources of type T."
- Zero-evidence rules stay functional (dampened) — seeds remain useful before curation catches up.
- Surface the gap list so evidence curation is a visible chore, not silent decay.

**Non-Goals:**
- Automatic evidence creation from literature ingestion (curation/extraction is separate work).
- Grading study quality beyond the existing `evidence_type` enum; no citation-count or journal-rank modeling.
- Weighting profile-constraint deltas (user's own assertions need no literature).

## Decisions

**1. Multiplier from typed evidence counts, clamped to [0.6, 1.3].**
Type weights: clinical 0.15, regulatory/safety 0.12, public_guidance 0.08, rule/definition 0.05 per linked active evidence row. `multiplier = clamp(0.6 + Σ type_weights, 0.6, 1.3)`. Zero evidence → 0.6. Rationale: bounded influence (evidence tunes, never dominates), monotonic in evidence, type-sensitive without pretending to meta-analysis. Constants live in one module dict — data-tunable later.

**2. Rule-scoped evidence counts; concern-scoped evidence does not transfer.**
Only `ConcernEvidence` rows pointing at the specific rule (`rule_id`) modulate that rule. Concern-level evidence (null rule) is contextual/documentation. Prevents one well-cited concern from inflating all its rules including speculative ones.

**3. Applied to concern-sourced deltas only, stacking multiplicatively with confidence (and position factor if present).**
`delta = round(weight × concern_confidence × evidence_multiplier [× position_factor])`, positive-delta floor of 1 retained. EXCLUDE-equivalent behavior does not exist for concern rules (AVOID never excludes), so no safety carve-out is needed beyond warnings remaining unscaled in emission.

**4. Prefetch evidence with rules; no per-formulation queries.**
Evidence counts are per-rule, resolved once per ranking run alongside the rule prefetch (`Prefetch("evidence")` or annotated counts per type). Formulation loop cost unchanged.

**5. `manage.py evidence_gaps`** prints active rules with zero rule-scoped evidence, grouped by concern, with rule keys — a curation worklist. Chosen over an admin view for zero-UI cost; admin can come later.

## Risks / Trade-offs

- **0.6 dampening shifts all current scores down on merge** (no rules have curated evidence yet) → mitigation: relative ordering within concern-rule effects is preserved; document the shift; optionally seed evidence for the strongest rules in the same PR.
- **Type weights are invented constants** → mitigation: bounded range caps the damage; single source of truth; spec pins the formula so changes are deliberate.
- **Double counting via multiple evidence rows citing the same paper** → mitigation: count distinct `literature_reference` per rule.
