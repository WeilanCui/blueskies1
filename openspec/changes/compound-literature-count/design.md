## Context

`get_literature_count` is the only consumer of `obj.literature_links` in `CompoundSerializer`. `CompoundViewSet.queryset` prefetches `literature_links` purely so that `len(obj.literature_links.all())` is cheap (cache read, no per-row query). The cubic suggestion to use `.count()` would, given that prefetch, issue a separate `SELECT COUNT(*)` for every compound — an N+1 in the list endpoint. The right move is to count in the database and drop the now-pointless prefetch of full rows.

## Goals / Non-Goals

**Goals:**
- Compute `literature_count` at the DB with no N+1 and without loading link rows.
- Keep the response identical (`literature_count` = number of links).
- Keep the serializer correct even if used on a Compound that wasn't annotated.

**Non-Goals:**
- No change to other prefetches (`aliases`, `identifiers`, `chemical_class_memberships`, `property_assertions`) — those rows are genuinely serialized.
- No API/shape change, no migration.

## Decisions

### Annotate instead of prefetch-for-count

`core/views.py`, `CompoundViewSet.queryset`:

```python
from django.db.models import Count  # add to existing django.db.models import

queryset = (
    Compound.objects.all()
    .select_related("structure")
    .annotate(literature_count=Count("literature_links"))
    .prefetch_related(
        "aliases",
        "identifiers",
        "chemical_class_memberships__chemical_class",
        "property_assertions__property_def",
        # "literature_links" removed — only needed for the count, now annotated
    )
)
```

`Count("literature_links")` is a grouped count resolved in the list query (a `LEFT OUTER JOIN ... GROUP BY`), so the whole page's counts come back in the main query — no extra round-trips.

### Annotation-aware getter with fallback

`core/serializers/compound.py`:

```python
def get_literature_count(self, obj: Compound) -> int:
    count = getattr(obj, "literature_count", None)
    if count is not None:
        return count
    return obj.literature_links.count()
```

- When the viewset annotation is present, this is a pure attribute read.
- The fallback (`.count()`, a single COUNT query) keeps the serializer correct if it is ever instantiated on a plain, non-annotated `Compound`. The fallback never loads all rows, so even the degraded path is better than the original `len(.all())` on a non-prefetched instance.

The `literature_count = serializers.SerializerMethodField()` declaration is unchanged; reading the model attribute `obj.literature_count` inside the method does not conflict with the SerializerMethodField.

## Risks / Trade-offs

- **Count semantics with joins:** `Count("literature_links")` counts related rows; with the other relations now prefetched (not joined), there is no fan-out multiplication risk in the main query. `Count` over a single to-many relation is exact.
- **Fallback divergence:** the fallback path uses `.count()`; both paths return the same integer, verified by a test that exercises the annotated endpoint and asserts the value.
- **Verification:** a query-count test (`assertNumQueries` / `CaptureQueriesContext`) on the list endpoint with multiple compounds ensures the annotation eliminated the per-compound count.
