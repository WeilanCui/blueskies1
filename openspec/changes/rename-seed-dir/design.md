## Context

`backend/seed/` holds 5 raw CSVs (~1.2MB: AB1, AB2, Prod1, Prod2, red1). The only code that locates them is `core/seeds/csv_catalog.py:9` — `DEFAULT_SEED_DIR = Path(__file__).resolve().parents[2] / "seed"` — consumed by `discover_csv_files()` / `iter_csv_product_rows()` and the `seed_catalog` management command. Two help/docstring strings in `seed_catalog.py` mention "seed/" cosmetically.

## Goals / Non-Goals

**Goals:**
- Eliminate the `seed` (data) vs `seeds` (code) naming collision by renaming the data dir to `data/`.
- Keep the `seed_catalog` command working with no behavior change.
- Preserve CSV git history.

**Non-Goals:**
- No CSV content changes.
- No git-lfs migration (deferred).
- No rename of the code packages `core/seeds/` or `literature/seeds/` (those are correctly named).

## Decisions

- `git mv backend/seed backend/data` (moves all 5 CSVs, history preserved).
- Edit exactly `csv_catalog.py:9`: `parents[2] / "seed"` → `parents[2] / "data"`. `parents[2]` from `backend/core/seeds/csv_catalog.py` resolves to `backend/`, so the new target is `backend/data` — correct.
- Update the two `seed_catalog.py` strings ("seed/*.csv", "seed/ folder") to "data/" for accuracy. These are help text only; no logic.

## Risks / Trade-offs

- **Missed path reference** would make seeding silently find zero CSVs. Mitigation: grep confirmed `csv_catalog.py:9` is the sole filesystem path; verify post-change that `discover_csv_files()` returns 5 files.
- **1.2MB stays in git**: accepted for now; LFS would add collaborator setup friction on a prototype.
