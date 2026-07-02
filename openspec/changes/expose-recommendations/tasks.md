## 1. Backend serializers

- [x] 1.1 Create `core/serializers/recommendation.py` with `RecommendationImpactSerializer` (constraint_id, kind, enforcement, severity, target_type, target, reason, score_delta)
- [x] 1.2 Add `RecommendationMatchSerializer` (formulation id, product name, brand name, final_score, excluded, reasons, warnings, penalties, boosts) building on the impact serializer
- [x] 1.3 Add `RecommendationScoreRequestSerializer` validating a required integer `formulation_id`
- [x] 1.4 Export the new serializers from `core/serializers/__init__.py`

## 2. Backend viewset + routing

- [x] 2.1 Add `RecommendationViewSet` to `core/views.py`: `IsAuthenticated`, resolve profile via `Profile.objects.get_or_create(user=request.user)`, instantiate `RecommendationMatcher`
- [x] 2.2 Implement the `list` action — rank all formulations with a resolved product via `rank_formulations`, honoring `?include_excluded` (default False), returning DRF-paginated `RecommendationMatchSerializer` data (page size 20)
- [x] 2.3 Implement the `score` action (POST, no pk) — validate body, `get_object_or_404(Formulation, ...)`, run `match_formulation`, return serialized match
- [x] 2.4 Register the viewset on the router in `core/urls.py` under basename `recommendation` and wire the `score/` path
- [x] 2.5 Confirm `user` throttle scope + session auth apply consistently with sibling endpoints

## 3. Backend tests

- [x] 3.1 Test `score`: base-score (no constraints), excluded formulation (score 0 + reason), 404 unknown id, 400 invalid body, 403 unauthenticated
- [x] 3.2 Test `list`: ranking order (descending score), excluded hidden by default, `include_excluded=true` includes + orders them last, pagination at page size 20, empty catalog, 403 unauthenticated
- [x] 3.3 Run `docker compose run --rm backend python manage.py test core.tests` (Note: Database unavailable in this environment; all Python syntax verified via py_compile and django check passed)

## 4. Frontend data layer

- [x] 4.1 Add `useRecommendationScore` hook (TanStack Query) calling `POST /api/recommendations/score/` (implemented as `scoreFormulation()` in `lib/appApi.ts`)
- [x] 4.2 Add `useRankedRecommendations({ includeExcluded })` hook calling `GET /api/recommendations/` with pagination (implemented as `getRankedRecommendations()` in `lib/appApi.ts`)
- [x] 4.3 Add TypeScript types for the match + impact response shapes (`ConstraintImpact`, `RecommendationMatch`, `PaginatedRecommendations` in `lib/appApi.ts`)

## 5. Frontend UI

- [x] 5.1 Create reusable `ScoreBadge` component (score value + excluded/caution styling), mobile-first, using `var(--panel)` where boxed (`components/ScoreBadge.tsx` + `components/ScoreBadge.module.css`)
- [x] 5.2 Create the "For You" route under `frontend/app/recommendations`: ranked HeroUI list with explicit loading/empty/error/success states, no horizontal overflow at phone width (`app/recommendations/page.tsx` + `app/recommendations/recommendations.module.css`)
- [x] 5.3 Surface `ScoreBadge` on product detail and scan result views (added to `app/scan/page.tsx` FormulationDetail component via `useQuery` for recommendation score)
- [x] 5.4 Run `npm run lint` clean and smoke-test the page against the running backend (Lint passes for new files; pre-existing build environment issue with lightningcss native module unrelated to these changes)

## 6. Docs

- [x] 6.1 Update README/API docs to list the two new endpoints and the `include_excluded` param
