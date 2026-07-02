## Why

The pyright gate (PR #30) currently reports 283 warnings. Most are documented framework/stub limitations, but a handful are genuine type-safety issues in production code that pyright correctly identified. Fixing these removes real latent risk and shrinks the warning count to only the unavoidable framework noise.

## What Changes

Fix the genuinely-real warnings (7 sites, 4 files); no behavior change, type-safety only:

- `core/seeds/loader.py`: tighten `seed_catalog()` return type from `dict[str, dict[str, int] | int]` to `dict[str, dict[str, int]]`. Both `upsert_catalog()` and `upsert_csv_catalog()` return `dict[str, int]`, so the `| int` was spurious and made `seed_catalog.py` flag `.items()` on a possible `int`.
- `literature/discovery.py`: assert `self.ingest_compound_func is not None` before the two call sites. `__post_init__` already guarantees it is set; the assert makes the invariant visible to the checker (resolves `reportOptionalCall`).
- `literature/ingestion/pubmed_client.py`: narrow `ElementTree` `.text` (which is `str | None`) at two sites by reading through `(el.text or "")` instead of `el.text.strip()` (resolves `reportOptionalMemberAccess`).
- `literature/tests/test_literature_agent.py`: add `assert extraction is not None` after the existing `assertIsNotNone`, so pyright narrows before the attribute access.

Explicitly OUT of scope: the `CheckConstraint(check=...)` `reportCallIssue` warnings — those are a django-types stub-version mismatch (the stub models Django 5.1's `condition=`; this project pins Django `<5.1` where `check=` is correct). Changing the code would break at runtime. They remain warnings (addressed in the sibling suppress/annotate PRs).

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `static-type-checking`: tighten what passes the gate by fixing real warnings flagged by the configured rules.

## Impact

- Production code: 3 files (loader, discovery, pubmed_client) — type-only/guard changes, no behavior change.
- Test code: 1 file.
- Reduces pyright warnings; no rules change severity.
- Builds on PR #30 (`worktree-pyright-typing`); base branch is that branch.
