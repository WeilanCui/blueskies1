## Context

PR #30 added the pyright gate at standard mode with documented rule downgrades. Of the 283 warnings, a small subset are real type-safety issues rather than stub/framework limitations. This change fixes only those, leaving the documented framework noise for the sibling PRs.

## Decisions

### Fix at source, behavior-preserving
Each fix is type-only or a guard that encodes an existing runtime invariant. No control flow or output changes.

- **seed_catalog return type** — narrowing `dict[str, dict[str, int] | int]` → `dict[str, dict[str, int]]` matches the actual returns of `upsert_catalog`/`upsert_csv_catalog` (both `dict[str, int]`). The `| int` was never produced.
- **discovery DI** — `assert self.ingest_compound_func is not None` over restructuring the dataclass field. `__post_init__` already assigns a default when None, so the assert documents a true invariant with minimal churn.
- **ElementTree .text** — `(el.text or "")` over `assert`. `.text` is `str | None`; the surrounding guards already test the text, so reading through `or ""` is equivalent and clearer than an assert.
- **test assert** — `assert extraction is not None` complements the existing `assertIsNotNone` (pyright does not treat unittest assertions as narrowing).

### Constraint warnings explicitly excluded
`CheckConstraint(check=...)` is correct on Django 5.0 (pinned `<5.1`). django-types ships the 5.1 signature (`condition=`). Editing the code to satisfy the stub would break runtime. Left as a warning; the sibling suppress PR handles it via `# pyright: ignore`.

## Risks / Trade-offs

- `assert` statements run at runtime; under `python -O` they are stripped. The asserted invariants are guaranteed by surrounding code, so stripping is harmless. Accepted.
- No risk to behavior; changes are localized.
