# Blueskies App Framework

A Docker Compose full-stack starter with:

- Django API
- PostgreSQL
- Redis
- Celery worker
- Next.js frontend

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Open:
```bash
npm run dev
```
- Frontend: http://localhost:3000
- Backend health check: http://localhost:8000/api/health/

## Common Commands

Run Django migrations:

```bash
docker compose run --rm backend python manage.py migrate
```

Create a Django superuser:

```bash
docker compose run --rm backend python manage.py createsuperuser
```

Run a sample Celery task from Django shell:

```bash
docker compose run --rm backend python manage.py shell
```

```python
from core.tasks import debug_task
debug_task.delay()
```

## Layout

```text
backend/
  config/       Django project settings, URLs, Celery app
  core/         Starter app with health endpoint and sample task
frontend/
  app/          Next.js app router UI and API proxy
docker-compose.yml
```

## Development Standards

Use [CODEX.md](./CODEX.md) as the project guideline for code quality, backend work, and frontend design. Frontend changes should be designed mobile-first and verified on mobile-width screens before handoff.
