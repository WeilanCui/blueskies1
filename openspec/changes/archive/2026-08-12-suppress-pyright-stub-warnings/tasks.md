# Tasks

## 1. Generate suppressions
- [x] 1.1 Run `pyright --outputjson` in the venv from this worktree; collect every warning's file, line, and rule.
- [x] 1.2 For each affected line, append a rule-specific `# pyright: ignore[...]` comment (merge + dedupe rules when a line has several). Idempotent; do not double-append.

## 2. Validation
- [x] 2.1 Re-run pyright in the venv → 0 errors, 0 warnings.
- [x] 2.2 `python manage.py check` passes (with deps + dummy env).
- [x] 2.3 Spot-check that ignores are rule-specific (no blanket `# type: ignore`).
- [x] 2.4 `openspec validate suppress-pyright-stub-warnings --strict` passes.
