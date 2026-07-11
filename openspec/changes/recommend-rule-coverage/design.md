## Context

`bridge-concern-rules` gives the engine a `ConcernRuleEvaluator` that resolves a user's concerns → rules and matches targets per formulation, but maps RECOMMEND to a zero-delta informational impact. Coverage needs aggregation *across* a concern's RECOMMEND rules (matched vs total), which the per-rule impact stream cannot express alone.

## Goals / Non-Goals

**Goals:**
- Per-(formulation, concern) coverage: `matched/total` RECOMMEND rules with matched/unmatched labels.
- Matched RECOMMEND rules add score (weight × confidence), so products serving a concern rank above inert ones.
- API + "For You"/score-detail UI surface coverage as the primary "why recommended" explanation.

**Non-Goals:**
- Routine-level coverage ("does the user's whole routine cover the concern") — a later, different aggregate.
- Diminishing returns / caps on stacked actives; concentration awareness (separate `ingredient-position-weighting` change).
- Re-sorting by coverage instead of score.

## Decisions

**1. Coverage computed inside `ConcernRuleEvaluator`, returned as a parallel structure.**
The evaluator already iterates concern→rules; it accumulates `CoverageSummary(concern_slug, matched: list[label], unmatched: list[label])` per concern while emitting one boost-group impact per matched RECOMMEND rule. Evaluation result gains `coverage: list[CoverageSummary]`. Alternative — deriving coverage in the serializer from impacts — rejected: unmatched rules produce no impacts, so the denominator would be lost.

**2. Matched RECOMMEND scores exactly like BOOST.**
Same formula (`+max(1, round(weight × confidence))`), same boosts group, `source="concern"`. Keeps one mental model for positive deltas; coverage summaries carry the RECOMMEND-specific meaning. Unmatched RECOMMEND rules contribute no negative delta (absence of a nicety is not a flaw).

**3. Zero-total concerns omitted.**
A concern with no active RECOMMEND rules produces no coverage entry (avoids "0 of 0" noise).

**4. Payload: top-level `coverage` array on the match, not per-impact.**
`[{concern, concern_label, matched_rules: [labels], total, matched}]`. Frontend renders one line per concern. Additive to the API contract.

## Risks / Trade-offs

- **Stacking inflation**: a product matching 4 recommended actives gains 4 boosts and can pin at 100 → mitigation: score already clamps at 100; ties broken by name remain stable; diminishing returns deferred until real data shows a problem.
- **Label quality**: coverage lines expose seed `label`s verbatim → mitigation: labels are human-authored in seeds; poor ones are data fixes.
