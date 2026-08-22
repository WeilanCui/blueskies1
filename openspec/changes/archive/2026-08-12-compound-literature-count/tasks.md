## 1. Backend change

- [x] 1.1 `backend/core/views.py`: add `Count` to the existing `from django.db.models import ...`; in `CompoundViewSet.queryset` add `.annotate(literature_count=Count("literature_links"))` and remove `"literature_links"` from `prefetch_related(...)`. Leave the other prefetches intact.
- [x] 1.2 `backend/core/serializers/compound.py`: change `get_literature_count` to return `getattr(obj, "literature_count", None)` when not None, else `obj.literature_links.count()`.

## 2. Tests

- [x] 2.1 Add a test (new file `backend/core/tests/test_compounds.py` or an existing suitable file) that creates a compound with a known number of literature links and asserts the serialized `literature_count` equals that number via the compound list/detail endpoint (`reverse("compound-list")` / `compound-detail`).
- [x] 2.2 Add a query-count test: create several compounds (each with links), hit the compound list endpoint inside `assertNumQueries` (or `CaptureQueriesContext`) and assert the query count does NOT scale per compound for the literature count (i.e. adding more compounds doesn't add count queries).
- [x] 2.3 Add a test for the non-annotated fallback: instantiate `CompoundSerializer(compound).data` directly on a freshly fetched `Compound` (no annotation) and assert `literature_count` is still correct.

## 3. Verify

- [x] 3.1 Full backend test suite passes (`pytest`) against PostgreSQL.
- [x] 3.2 `manage.py check` clean; `manage.py makemigrations --check --dry-run` reports "No changes detected".
- [x] 3.3 `openspec validate compound-literature-count --strict` passes.
