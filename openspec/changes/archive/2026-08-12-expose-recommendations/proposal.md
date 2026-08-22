## Why

The `RecommendationMatcher` engine (`core/profiles/recommendations.py`) already scores and ranks formulations against a user's profile constraints, and it is tested — but no REST endpoint exposes it, so the frontend cannot turn a user's skin concerns and a product's ingredients into visible recommendations. This change closes that gap: it makes the existing, working matching logic reachable by users.

## What Changes

- Add `POST /api/recommendations/score/` — score a single formulation for the authenticated user, returning the final score plus warnings/penalties/boosts/reasons ("Is this good for me?").
- Add `GET /api/recommendations/` — rank the catalog for the authenticated user, best-first, paginated (20/page). Hard-excluded products are dropped by default; `?include_excluded=true` returns the "products to avoid" view.
- Add a `RecommendationViewSet` in `core/views.py` and a new serializer module `core/serializers/recommendation.py`.
- Frontend: TanStack Query hooks (`useRecommendationScore`, `useRankedRecommendations`), a "For You" ranked list page, and a reusable score badge component surfaced on product/scan detail.

## Capabilities

### New Capabilities
- `recommendation-api`: Authenticated REST access to the profile-vs-formulation recommendation engine — single-product scoring and paginated catalog ranking — plus the frontend surfaces that consume it.

### Modified Capabilities
<!-- None: no existing spec-level behavior changes. The engine and data model already exist. -->

## Impact

- **Backend**: `core/views.py` (new viewset + URL registration in `core/urls.py`), new `core/serializers/recommendation.py`. Reuses existing `RecommendationMatcher` / `ProfileConstraintEvaluator` — no engine or data-model changes. DRF throttling (`user` scope) and session auth apply.
- **Frontend**: new hooks under `frontend/app` query layer, a new "For You" route, a score badge component reused on product/scan detail. TanStack Query + HeroUI, mobile-first.
- **Performance**: catalog ranking runs several `exists()` queries per formulation (N×M). Acceptable at prototype catalog size; query optimization (prefetch/annotate) is explicitly deferred to a follow-up.
- **No migrations** — models unchanged.
