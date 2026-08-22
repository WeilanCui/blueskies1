## Why

After the real-warning fixes (PR #32), the pyright gate still reports ~277 warnings — all documented framework/stub limitations (django-types reverse relations, abstract-model `Meta`, django-environ/TextChoices, DRF `ReturnDict`/overrides, celery `.delay`, a CheckConstraint stub-version mismatch). This change drives the warning count to ~0 by suppressing each at its source with a targeted `# pyright: ignore[<rule>]`, so a clean `pyright` run means "no unreviewed diagnostics" and any NEW warning stands out immediately.

## What Changes

- Append a targeted `# pyright: ignore[<rule>]` comment to every line that currently emits a framework/stub-limitation warning. Ignores are rule-specific (not blanket `# type: ignore`), so an unrelated future error on the same line is still reported.
- Where a line emits multiple such rules, combine them: `# pyright: ignore[ruleA, ruleB]`.
- Generated deterministically from `pyright --outputjson` to guarantee exact site coverage and avoid hand-edit drift.
- This is an ALTERNATIVE to the sibling annotate change (#PR3); only one of the two should be merged.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `static-type-checking`: bring the gate to a zero-warning baseline via source-level suppression of stub-limitation diagnostics.

## Impact

- Touches many production + test files with comment-only additions (no code logic changes).
- After this change, a single new warning becomes visible signal rather than lost in noise.
- Builds on PR #32 (`worktree-pyright-fix-real`).
- Trade-off vs the annotate PR: zero code churn / many ignore comments, vs. real annotations. Mutually exclusive — merge one.
