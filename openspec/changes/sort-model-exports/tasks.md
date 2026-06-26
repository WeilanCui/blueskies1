## 1. Reorder exports

- [x] 1.1 Sort `from core.models.<module>` import blocks alphabetically by module.
- [x] 1.2 Sort names within each import block alphabetically.
- [x] 1.3 Sort the `__all__` list alphabetically.

## 2. Verify

- [x] 2.1 Exported name-set identical before/after (66 names, guarded by parse+assert).
- [x] 2.2 `manage.py check` clean.
- [x] 2.3 `manage.py makemigrations --check --dry-run` reports "No changes detected".
