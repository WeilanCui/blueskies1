"""Paging helpers for the catalog search endpoints.

The plain catalog list endpoints serialize every matching row. That is fine for
the small server-rendered slices they were written for, but a browsable search
runs over ~1.6k products and ~5.9k compounds, so these endpoints hand back one
bounded page plus the size of the whole match set.
"""

DEFAULT_LIMIT = 25
MAX_LIMIT = 100


def _bounded_int(raw, default: int, maximum: int | None = None) -> int:
    """Parse a positive query-param int, falling back rather than erroring.

    Paging params come straight from a URL, so garbage is expected traffic and
    not worth a 400: an unreadable or out-of-range value means the caller gets
    the default page rather than an error page.
    """
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    if value < 1:
        return default
    if maximum is not None:
        return min(value, maximum)
    return value


def paged_search(queryset, serialize, request) -> dict:
    """Serialize one page of `queryset` into the search envelope.

    `count` is deliberately the total number of matches, not the length of
    `results` — the UI reports "N matches" while showing one page of them.
    """
    query = request.query_params.get("q", "").strip()
    limit = _bounded_int(request.query_params.get("limit"), DEFAULT_LIMIT, MAX_LIMIT)
    page = _bounded_int(request.query_params.get("page"), 1)
    offset = (page - 1) * limit

    return {
        "query": query,
        "limit": limit,
        "page": page,
        "count": queryset.count(),
        "results": [serialize(obj) for obj in queryset[offset : offset + limit]],
    }
