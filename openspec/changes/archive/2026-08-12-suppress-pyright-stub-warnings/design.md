## Context

PR #30 set up pyright with several rules downgraded to `warning` because they fire on framework/stub limitations. PR #32 fixed the genuinely-real warnings. The ~277 remaining are all noise. Goal: zero-warning baseline so new diagnostics are visible.

## Decisions

### Rule-specific inline ignores, generated deterministically
- Use `# pyright: ignore[<rule>]` (NOT blanket `# type: ignore`) so each suppression is scoped to the exact known-noisy rule; a different real error on the same line still surfaces.
- Generate the edits from `pyright --outputjson`: for each warning, append (or merge into an existing) ignore comment on the diagnostic's line. This guarantees the set matches what pyright actually reports and is reproducible.
- Idempotent: re-running must not duplicate comments.

### Why suppress rather than re-set rules to "none"
Setting the rules to `"none"` in `pyrightconfig.json` (as PR #30 partially does for stub-absence rules) disables them everywhere, including future real hits. Inline ignores keep the rules active so a NEW occurrence at a different site is still reported. This is the point of the zero-warning baseline.

### Multi-rule lines
A line emitting two rules gets `# pyright: ignore[ruleA, ruleB]`. The generator deduplicates and sorts rule names for stable output.

## Risks / Trade-offs

- **Comment noise**: many files gain ignore comments. This is the explicit cost of approach B; the sibling annotate change is the alternative. Mutually exclusive.
- **Over-suppression drift**: if code at an ignored line later changes so the warning no longer applies, the now-unnecessary ignore lingers. pyright reports unnecessary ignores only under `reportUnnecessaryTypeIgnoreComment` (not enabled); acceptable for this baseline.
- **Stub upgrades**: when django-types/DRF stubs improve, some ignores become unnecessary but harmless.

## Verification

- `pyright` in the venv → 0 errors, 0 (or near-0) warnings.
- `manage.py check` still passes (comments are inert).
