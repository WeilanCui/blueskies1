# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Blueskies is a skincare intelligence prototype: a Django REST API + Celery backend and a Next.js frontend, wired together with Docker Compose. The domain centers on resolving product INCI lists into a canonical **Compound** identity graph, then attaching provenance-backed property/literature/interaction assertions enriched from external sources (INCI API, PubChem, PubMed, OpenAI).

## Commands

All backend commands run inside the `backend` container.

```bash
# Start backend stack (db, redis, backend, celery worker, celery-beat)
docker compose up --build

# Start the frontend in Docker dev mode when needed
docker compose --profile frontend up --build frontend

# Migrations
docker compose run --rm backend python manage.py migrate
docker compose run --rm backend python manage.py makemigrations

# Superuser
docker compose run --rm backend python manage.py createsuperuser

# Backend tests (whole suite)
docker compose run --rm backend python manage.py test core.tests literature.tests
# Single module / single test
docker compose run --rm backend python manage.py test core.tests.test_routines
docker compose run --rm backend python manage.py test core.tests.test_routines.RoutineTestCase.test_method
```

Frontend (from `frontend/`):

```bash
npm run dev      # hot reload, daily work
npm run build && npm start   # production smoke test (standalone output)
npm run lint     # biome check
npm run format   # biome format --write
```

Do not run `npm start` without a fresh `npm run build` — it runs the standalone `.next` output with no file watching.

URLs: frontend `http://localhost:3000`, backend health `http://localhost:8000/api/health/`, Django admin `http://localhost:8000/admin/`.

## Backend architecture

Two Django apps: `core` (domain models, API, profiles, services) and `literature` (external ingestion + literature enrichment). Routing: `config/urls.py` → `core/urls.py` mounts a DRF `DefaultRouter` under `/api/` plus explicit paths for `health/`, `intake/`, `contact/`, `formulations/submit/`, `products/scan-barcode/`.

**Compound identity graph** is the heart of the data model (see `.cursor/plans/blueskies_model_diagram_*.plan.md` for the full ER diagram):
- `Compound` is the canonical ingredient identity (`canonical_inci` unique), with `CompoundAlias`/`CompoundIdentifier`/`CompoundStructure` satellites.
- `Formulation` → `FormulationIngredient` (position in INCI list) → resolved `Compound` (`SET_NULL`).
- Claims attach via the abstract `SourceMetadata` provenance mixin (`core/models/metadata.py`): `PropertyAssertion` (compound XOR formulation, supports `superseded_by` versioning), `CompoundLiterature`, `CompoundRelationship`, `InteractionAssertion`.
- Vocabulary/seed models: `PropertyDefinition`, `GlossaryTerm`, `InteractionRule`.

**Model file layout (enforced by `.cursor/rules/django-model-files.mdc`):** one primary model per file under `core/models/`, re-exported from `core/models/__init__.py`. Do NOT append new models to `profiles.py` or other aggregate files. File-only moves (same app label + class) need no migration.

**Ingestion & enrichment** live in `literature/ingestion/` (`formulation_ingest.py`, `inci_ingest.py`, `ingest.py`, plus `pubchem_client.py`, `pubmed_client.py`, `inci_client.py`) and `literature/enrichment/`. External API bases/keys come from settings (`INCI_API_*`, `EPA_UV_API_BASE`, `OPENAI_*`, `LITERATURE_EXTRACTOR`). Note: the cursor plan references `core/ingestion/` — actual path is `literature/ingestion/`.

**Profiles** (`core/profiles/`): `constraints.py`, `recommendations.py`, and `matching.py` implement flexible per-user constraint matching (hard exclusions, cautions, penalties, boosts, informational). Recommendation matching is extensible via injectable `extra_evaluators` — `skinconcerns/scoring.py` provides `ConcernRuleEvaluator` which scores live `ConcernRule`s from selected skin concerns (reads concerns' active rules, matches them against formulations, scales delta by confidence). Concern rules produce impacts marked `source="concern"` alongside constraint impacts (`source="constraint"`). Note: AVOID rules produce warning-level impacts and negative deltas (caution + penalty, not exclusion).

**Position-weighted scoring**: `FormulationIngredient.position` encodes INCI list order (a concentration proxy under industry standards). Ingredient-targeted constraint/concern-rule matches apply a position factor `max(0.3, 1.0 − 0.7 × (position − 1) / max(total − 1, 1))` to PENALIZE/BOOST/RECOMMEND deltas: position 1 (top) → factor 1.0, last position → floor 0.3, single-ingredient → 1.0, missing position/total → 1.0 (current behavior). EXCLUDE hard exclusions and WARN/AVOID warnings stay unscaled (safety signals must not fade with concentration). Non-ingredient targets (property, raw label, product category) never get position scaling. The computed position_factor is exposed on impacts (nullable) for UI explanation of concentration-adjusted deltas.

**Evidence-weighted scoring**: Concern-rule score deltas are modulated by an evidence multiplier computed from linked `ConcernEvidence` rows. The multiplier formula is:
```
multiplier = clamp(0.6 + Σ(type_weight for each distinct literature reference), 0.6, 1.3)
```
Type weights: clinical 0.15, regulatory/safety 0.12, public_guidance 0.08, rule/definition 0.05. Only **rule-scoped** evidence (evidence rows where `rule_id` is not null) contributes; concern-scoped evidence (null rule) is informational only. Deduplication occurs per distinct `literature_reference_id` (the same reference cited in multiple evidence rows counts once at the max type weight). Multiplier is computed once per rule in `ConcernRuleEvaluator.prepare()` and cached in context. Rules with zero evidence get multiplier 0.6 (dampened but still active); with evidence the multiplier scales up to 1.3. Concern-sourced impacts expose `evidence_count` (distinct references) and `evidence_multiplier` for UI rendering. Profile-constraint deltas are unaffected (user assertions need no literature backing). Management command `manage.py evidence_gaps` lists all active rules with zero rule-scoped evidence, grouped by concern slug, enabling curation workflows.

**Celery**: app defined in `config/celery.py`, broker/result on Redis. `core/tasks.py` holds `@shared_task`s; `daily_literature_discovery_task` runs nightly via `CELERY_BEAT_SCHEDULE` (configurable through `LITERATURE_DAILY_*` env vars). Keep tasks idempotent and observable.

**API conventions**: DRF throttling is enabled with named scopes (`anon`, `user`, `auth`, `signup`, `contact`, `formulation_submit`) — see `core/throttles.py` and `REST_FRAMEWORK` settings; rates are env-overridable. Auth is session-based via `SessionAuthViewSet`. Keep request/response logic in views/viewsets, domain behavior in model methods.

**Catalog search endpoints** back the `/skincareApi` page. Both return the same envelope — `{query, limit, page, count, results}`, where `count` is the size of the whole match set, not of `results`. Paging comes from `core/search.py` (`limit` defaults to 25, hard ceiling 100; unparseable values fall back rather than 400):
- `GET /api/products/search/?q=&limit=&page=` — same filter as the product list (name, display_name, category, description, brand), serialized with `serialize_catalog_product`.
- `GET /api/compounds/search/?q=&limit=&page=` — matches `canonical_inci`, `display_name` and aliases; returns light `{id, ingredient}` rows, not the full compound serializer.

The plain `/api/products/` and `/api/compounds/` list endpoints stay unpaged — existing callers rely on getting the whole array, so search was added alongside them rather than changing them.

**Recommendation endpoints** (`RecommendationViewSet`):
- `POST /api/recommendations/score/` — score a single formulation against the authenticated user's profile constraints and concern rules. Request: `{ "formulation_id": <id> }`. Response: `RecommendationMatch` with final_score, excluded, reasons, impact groups (warnings, penalties, boosts), and coverage array. Each impact includes `source` ("constraint" or "concern") and concern-sourced impacts include `concern` (slug). Coverage array lists per-concern RECOMMEND rule coverage: `{ concern (slug), concern_label, matched, total, matched_rules (list of matched labels) }`.
- `GET /api/recommendations/` — rank all formulations with a resolved product against the authenticated user's profile, paginated (20 per page), best-first. Query param `?include_excluded=true` includes hard-excluded formulations (sorted after non-excluded ones); default is false. Response: paginated list of `RecommendationMatch` objects with concern impacts and coverage included.

**Data confidence** (`core/profiles/confidence.py`): Each recommendation match carries `data_confidence` (0–1, rounded 2dp) and `confidence_band` ("high"/"medium"/"low") reflecting the fraction of the formulation's ingredients resolved to compounds. Confidence measures **knowledge**, not quality: high confidence means "we understand the ingredient list"; low confidence means "the label is incomplete or unparsed." Bands are: high ≥ 0.8, medium ≥ 0.4, low < 0.4. Formulations with zero ingredients return 0.0; those with pending enrichment are capped at 0.5. Ranking uses confidence as a tie-breaker (after final score): equal scores rank high-confidence before medium before low, ensuring well-understood products rank above mysterious score-100 products.

## Frontend architecture

Next.js 16 App Router under `frontend/app/` (routes: `home`, `login`, `intake`, `compounds`, `skincareApi`, `scan`, `routine`, `reactions`, `experience`; server route handlers under `app/api/`). Stack: HeroUI components, Tailwind v4, TanStack Query, `@zxing/library` for barcode scanning. Lint/format via Biome.

Conventions (from `CODEX.md`):
- **Mobile-first** is mandatory — every screen must work at phone width with no horizontal overflow; design loading/empty/error/success states explicitly.
- Use **HeroUI** for buttons/forms/cards/modals; use **TanStack Query** for client-side API fetching/mutations. Raw `fetch` only in route handlers / server-side utilities.
- Use `var(--panel)` (`#eef6fc`, light blue) for boxed surfaces (cards, panels, list items).

## Deployment (Docker Swarm)

`service-compose.yml` is the stack file; `make push` publishes the images it references to
`direct:5000`. Only one service is reachable from outside the swarm: **`web` (Next.js,
port 3000)**. Django runs privately — the browser already talks only to the route handlers
in `app/api/`, which proxy via `lib/backendProxy.ts` at `SERVER_API_BASE_URL`.

Things to preserve when changing this area:

- Both Dockerfiles are **multi-stage** (`dev` and `prod`). `docker-compose.yml` pins
  `target: dev` on every built service — without that pin, compose builds the last stage,
  which is production. Keep the `dev` stages in sync when adding dependencies.
- `next.config.ts` `rewrites()` (admin at `/admin`, its assets at `/django-static`) is
  evaluated at **build time**, so `frontend/Dockerfile` passes `SERVER_API_BASE_URL` as a
  build `ARG`. The `:path*` destinations deliberately re-append the trailing slash Next
  strips, or Django's `APPEND_SLASH` loops.
- `backend/deploy/entrypoint.sh` derives the Celery/cache URLs from one `REDIS_URL`, waits
  for Postgres, and runs `migrate` **only when `DJANGO_MIGRATE_ON_START` is set** — which
  the stack file sets on `backend` alone. Celery and beat share the image and must not
  migrate. This keeps `backend` at `replicas: 1` by necessity, not preference.
- `docker exec` bypasses the entrypoint, so run management commands as
  `/app/deploy/entrypoint.sh python manage.py ...`.
- `settings.py` keeps the discrete `POSTGRES_*` path; `DJANGO_CACHE_URL` switches DRF
  throttle counters from per-process LocMemCache to shared Redis.
- The `web` image must keep `curl` and answer 2xx at `/` — that is its healthcheck.

## Conventions reference

`CODEX.md` holds the full engineering checklist (backend, frontend, styling, review). Commit migrations alongside model changes. Update README/docs when setup or behavior changes.
