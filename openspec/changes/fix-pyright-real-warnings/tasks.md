# Tasks

## 1. Source fixes
- [x] 1.1 `core/seeds/loader.py`: change `seed_catalog()` return annotation and the `results` local annotation from `dict[str, dict[str, int] | int]` to `dict[str, dict[str, int]]`.
- [x] 1.2 `literature/discovery.py`: add `assert self.ingest_compound_func is not None` immediately before the call at ~line 792 and the call at ~line 900.
- [x] 1.3 `literature/ingestion/pubmed_client.py`: at ~line 87 change `pmid = pmid_el.text.strip()` to `pmid = (pmid_el.text or "").strip()`; at ~line 138 change `return int(el.text.strip())` to `return int((el.text or "").strip())`.
- [x] 1.4 `literature/tests/test_literature_agent.py`: add `assert extraction is not None` after the existing `self.assertIsNotNone(extraction)` (before `extraction.functional_classes`).

## 2. Validation
- [ ] 2.1 Run pyright in the project venv; confirm the four targeted rules no longer fire at these sites and 0 errors remain.
- [ ] 2.2 `python manage.py check` passes (with deps + dummy env).
- [ ] 2.3 `openspec validate fix-pyright-real-warnings --strict` passes.
