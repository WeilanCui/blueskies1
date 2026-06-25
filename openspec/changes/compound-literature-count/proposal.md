## Why

`CompoundSerializer.get_literature_count` (`backend/core/serializers/compound.py`) returns `len(obj.literature_links.all())`. cubic flagged this (issue #26) as loading all rows to count them. The naive fix — `obj.literature_links.count()` — is actually a **regression here**: `CompoundViewSet.queryset` does `.prefetch_related("literature_links")` (`core/views.py`), so `len(...all())` already reads from the prefetch cache with zero extra queries, while `.count()` issues a fresh `SELECT COUNT(*)` per compound → N+1 in the list view.

Crucially, `literature_links` is prefetched **solely** to feed this count — it has no other consumer in `CompoundSerializer`. So the correct optimization is to count at the database with an annotation and stop loading the link rows entirely.

## What Changes

- `CompoundViewSet.queryset` (`core/views.py`): drop `"literature_links"` from `prefetch_related(...)` and add `.annotate(literature_count=Count("literature_links"))`.
- `CompoundSerializer.get_literature_count`: return the annotated `obj.literature_count` when present, falling back to `obj.literature_links.count()` if the serializer is used on a non-annotated instance.
- Net effect: the literature count is computed by a single grouped DB COUNT for the whole page; no per-row loading, no N+1.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities

- `compound-api`: `literature_count` is computed at the database; the compound list/detail no longer loads all literature-link rows.

## Impact

- Files: `backend/core/views.py` (CompoundViewSet queryset), `backend/core/serializers/compound.py` (`get_literature_count`).
- Response shape unchanged: `literature_count` is still an integer equal to the number of links.
- Tests: assert the count value is correct AND that the compound list view does not issue per-compound count queries (query-count assertion).
- No migration. Based off PR #23 (the serializers split); independent of the routine-chain PRs (#27/#28).
