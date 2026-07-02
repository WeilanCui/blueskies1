## 1. Evidence strength

- [ ] 1.1 `skinconcerns/scoring.py`: `evidence_multiplier(rule) -> float` — clamp(0.6 + Σ type weights over distinct rule-scoped active references, 0.6, 1.3); type-weight dict as module constant
- [ ] 1.2 Prefetch/annotate per-type distinct-reference counts alongside the rule prefetch (no per-formulation queries)

## 2. Scoring integration

- [ ] 2.1 Concern delta becomes `round(weight × concern_confidence × evidence_multiplier)` (× position_factor if that change landed); positive floor 1 retained
- [ ] 2.2 Concern-sourced impacts carry `evidence_count` + `evidence_multiplier`; serializer + frontend types additive

## 3. Curation report

- [ ] 3.1 `manage.py evidence_gaps`: active zero-evidence rules grouped by concern (slug + rule key)

## 4. Tests

- [ ] 4.1 Multiplier: zero-evidence 0.6, clinical accumulation, cap, concern-level non-transfer, duplicate-citation dedup
- [ ] 4.2 Scoring: dampened vs evidenced rule deltas; constraints unaffected
- [ ] 4.3 API shape; command output; full suite green

## 5. Docs

- [ ] 5.1 Document formula + curation workflow (evidence_gaps) in README/CLAUDE.md
