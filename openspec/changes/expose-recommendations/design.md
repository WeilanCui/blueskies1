## Context

The recommendation engine already exists and is tested: `RecommendationMatcher` (`core/profiles/recommendations.py`) delegates to `ProfileConstraintEvaluator` (`core/profiles/constraints.py`) to score a `Formulation` against a `Profile`'s active `ProfileConstraint`s. It returns a `RecommendationMatch` (dataclass) carrying `final_score`, `excluded`, and grouped `ConstraintImpact` lists (warnings/penalties/boosts/matched_constraints) with human-readable reasons.

Nothing exposes this over HTTP. Every personal endpoint in `core/views.py` follows one pattern: `IsAuthenticated`, then `Profile.objects.get_or_create(user=request.user)`. Serializers live in the `core/serializers/` package (one module per domain). This change adds a thin API + serializer layer over the engine, then a frontend that consumes it.

## Goals / Non-Goals

**Goals:**
- Expose single-formulation scoring and paginated catalog ranking as authenticated REST endpoints.
- Serialize `RecommendationMatch` / `ConstraintImpact` faithfully (score, excluded, reasons, impact groups).
- Deliver a user-visible "For You" ranked page and a reusable score badge on product/scan detail.
- Reuse the engine untouched — no changes to matching logic or data model.

**Non-Goals:**
- No changes to `RecommendationMatcher` / `ProfileConstraintEvaluator` logic or scoring weights.
- No query optimization of the N×M `exists()` pattern (deferred follow-up).
- No candidate pre-filtering (by concern/category/brand) — rank the full catalog.
- No new models, no migrations, no Amazon ESCI, no skin analyzer.

## Decisions

**1. One `RecommendationViewSet` in `core/views.py`, two actions.**
`score` (POST, detail-less action → `/api/recommendations/score/`) and `list` (GET → `/api/recommendations/`). Registered on the existing DRF `DefaultRouter` in `core/urls.py` under basename `recommendation`. Alternative — two standalone `APIView`s — rejected for consistency with the router-based layout already in use.

**2. Profile resolution mirrors existing endpoints.** `Profile.objects.get_or_create(user=request.user)` inside the view; `IsAuthenticated`. A user with no constraints yet gets base scores (100) — a valid, non-error state.

**3. Serializers are read-only, hand-built from the dataclass** (not `ModelSerializer`, since `RecommendationMatch` is not a model). `RecommendationImpactSerializer` (kind, enforcement, severity, target_type, target, reason, score_delta) and `RecommendationMatchSerializer` (formulation id, product name + brand, final_score, excluded, reasons, warnings, penalties, boosts). The `score` request body is validated by a small `RecommendationScoreRequestSerializer` (`formulation_id`, integer, required).

**4. Ranking uses the engine's own ordering + DRF pagination.** Call `matcher.rank_formulations(profile, formulations, include_excluded=<param>)` where `formulations` is every `Formulation` with a non-null `product`. `include_excluded` defaults `False`; `?include_excluded=true` flips it. Page size 20 via DRF `PageNumberPagination`. The engine already sorts `(excluded, -final_score, product.name, id)`.

**5. Frontend: hooks + one route + one component.**
- `useRecommendationScore(formulationId)` (mutation/query) → POST score.
- `useRankedRecommendations({ includeExcluded })` → GET list, paginated.
- New route `frontend/app/recommendations` ("For You"): ranked HeroUI list, explicit loading/empty/error/success states, mobile-first, `var(--panel)` surfaces.
- `ScoreBadge` component (score + excluded/warn styling) reused on product and scan detail.

## Risks / Trade-offs

- **N×M query cost on ranking** → mitigation: full catalog is prototype-sized; page size caps response work; optimization flagged as a follow-up, not silently ignored.
- **Empty profile / empty catalog** → mitigation: both are valid states; endpoints return base-scored results or an empty page, and the frontend renders explicit empty states rather than errors.
- **`views.py` already large (622 lines)** → mitigation: adding one focused viewset is consistent with current structure; the broader views.py split is a separate, already-identified cleanup and out of scope here.
- **Excluded products hidden by default could surprise users wanting to see "why avoided"** → mitigation: `?include_excluded=true` surfaces them, and `score` on a single product always returns the exclusion reason.
