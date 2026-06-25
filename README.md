# Blueskies

Blueskies is a skincare intelligence app in progress. The product vision is to
help people understand their skin, capture their current regimen, scan products,
track skin changes over time, and connect those changes to ingredients,
formulations, weather/location, hormone cycle context, and product history.

The app is currently a prototype and roadmap build, not a fully working consumer
product.

## What It Shows Today

- A roadmap landing page for users and investors at `/`
- A contact form that stores name, email, and feedback for admin follow-up
- Login/signup at `/login` and a mobile-friendly skin intake at `/intake`
- A compound browser backed by the Django API at `/compounds`
- A skincare catalog prototype at `/skincareApi`
- Backend ingredient/formulation models, literature enrichment, and profile
  constraint matching services

## Product Direction

Blueskies is being designed around a simple loop:

1. Analyze skin state from intake and future photo-based signals.
2. Build a flexible skin profile with goals, sensitivities, lifestyle context,
   hormone/cycle context, weather/location, and changing skin state.
3. Capture the user’s regimen through product photos, barcode scans, search, or
   ingredient lists.
4. Use ingredient science, formulation intelligence, and journal-backed evidence
   to explain how products may work for that person.
5. Track outcomes over time so recommendations can improve from both science and
   personal history.

The recommendation layer is intentionally flexible. Personal constraints can be
hard exclusions, cautions, penalties, boosts, or informational matches rather
than a brittle rule list.

## Tech Stack

- Django API
- Django REST Framework
- PostgreSQL
- Redis
- Celery worker
- Next.js frontend
- Docker Compose for local services

## Quick Start

Create an environment file:

```bash
cp .env.example .env
```

Start the full stack:

```bash
docker compose up --build
```

The frontend container installs its npm dependencies before starting, so rebuilt
images and reused compose volumes stay in sync with `frontend/package-lock.json`.

Open:

- Frontend: http://localhost:3000
- Backend health check: http://localhost:8000/api/health/

You can also run the frontend directly:

```bash
cd frontend
npm install
npm run dev
```

If port `3000` is occupied, Next.js will use the next available port.

## Common Commands

Run Django migrations:

```bash
docker compose run --rm backend python manage.py migrate
```

Create a Django superuser:

```bash
docker compose run --rm backend python manage.py createsuperuser
```

Run backend tests:

```bash
docker compose run --rm backend python manage.py test core.tests
```

Build the frontend:

```bash
cd frontend
npm run build
```

Linting is configured as `npm run lint`, but the script currently expects a
`biome` binary that is not installed in `frontend/package.json`.

## Backend Notes

The backend includes:

- Ingredient and compound models
- Formulation and formulation ingredient models
- Chemical class membership
- Literature reference/enrichment models
- Profile and versioned skin profile models
- Flexible `ProfileConstraint` rows for allergies, sensitivities, avoids,
  preferences, cautions, goals, and lifestyle constraints
- `ProfileConstraintEvaluator` and `RecommendationMatcher` services for matching
  products against personal constraints
- `ContactSubmission` records from the landing-page contact form, visible in
  Django admin

### Type checking

The repository uses [pyright](https://github.com/microsoft/pyright) for static type checking. To set up:

```bash
pip install -r backend/requirements-dev.txt
pre-commit install
```

The `pyright` hook runs on every commit, configured via `pyrightconfig.json` at standard type-checking mode scoped to the `backend/` directory. See that file for configuration details.

## Layout

```text
backend/
  config/       Django project settings, URLs, Celery app
  core/         Domain models, ingestion, enrichment, profile services, tests
frontend/
  app/          Next.js app router pages and API proxy routes
  components/   Shared UI components
docker-compose.yml
```

## Development Standards

Use [CODEX.md](./CODEX.md) as the project guideline for code quality, backend
work, and frontend design. Frontend changes should be designed mobile-first and
verified on mobile-width screens before handoff.

## Data
Seed basic sample data
```bash
docker compose exec backend python manage.py seed_catalog
```
