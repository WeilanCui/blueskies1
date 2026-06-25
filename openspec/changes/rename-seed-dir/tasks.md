## 1. Rename directory

- [x] 1.1 `git mv backend/seed backend/data` (all 5 CSVs).

## 2. Update references

- [x] 2.1 `core/seeds/csv_catalog.py:9` — change `parents[2] / "seed"` → `parents[2] / "data"`.
- [x] 2.2 `core/management/commands/seed_catalog.py` — update the two help/docstring strings mentioning "seed/" to "data/".

## 3. Verify

- [x] 3.1 `backend/seed/` gone; `backend/data/` has the 5 CSVs.
- [x] 3.2 `grep -rn '/ "seed"' backend --include=*.py` returns nothing.
- [x] 3.3 `discover_csv_files()` returns 5 files (run via docker: `manage.py shell -c "from core.seeds.csv_catalog import discover_csv_files; print(len(discover_csv_files()))"`).
- [x] 3.4 `manage.py check` clean.
