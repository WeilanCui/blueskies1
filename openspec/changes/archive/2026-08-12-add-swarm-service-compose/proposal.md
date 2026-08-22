## Why

The repository can build and publish images (`Makefile` → `direct:5000`), but nothing
describes how those images run as a Docker Swarm stack. `docker-compose.yml` is
development-only: it bind-mounts source over `/app`, runs `manage.py runserver` and
`next dev`, publishes ports directly to the host, and has no `deploy:` blocks at all.

The images themselves are also not runnable unattended. Both Dockerfiles are single-stage
with **no `CMD`** — the command comes from compose. Django serves no static files in
production (`STATIC_ROOT` is unset, no WSGI server is installed), so the admin would load
without styling even if the container started.

## What Changes

- Add `service-compose.yml`, a Swarm stack file following the conventions of the stacks in
  `~/workspace/tempest/docker/`: `deploy:` blocks with resource limits and placement
  constraints, an encrypted overlay network, `/mnt/persist/<stack>/` bind mounts, Traefik
  routing labels, and the house healthcheck shape.
- Add production stages to both Dockerfiles. `backend`: `base -> dev | prod`, where `prod`
  runs `collectstatic` at build time and serves via gunicorn. `frontend`:
  `deps -> dev | builder -> prod`, where `prod` carries only the Next.js standalone output.
- Add `backend/deploy/entrypoint.sh`, which normalises Redis configuration, waits for the
  database, and applies migrations before exec'ing the service command. Migration is gated
  on `DJANGO_MIGRATE_ON_START`, set only on the Django service — Celery worker and beat
  share the image and must not migrate concurrently with it.
- Pin `docker-compose.yml` to the new `dev` targets so local development is unchanged.
- Add `gunicorn` and `whitenoise` to `backend/requirements.txt`; set `STATIC_ROOT` and a
  WhiteNoise storage backend in `settings.py` so the Django admin renders.
- `web` (Next.js) is the only externally reachable service, routed by Traefik at
  `blueskies1.tempestnetworks.net`. Django, Celery, Beat, Postgres and Redis sit on a
  private overlay. This needs no frontend rewiring — the browser already talks only to the
  Next route handlers in `app/api/`, which proxy to Django via `lib/backendProxy.ts`.
- Proxy `/admin` and `/django-static` through the Next.js server via `next.config.ts`
  rewrites, since Django is not reachable from outside the swarm.

## Capabilities

### New Capabilities
- `swarm-deployment`: Running the published images as a Docker Swarm stack — service
  topology, ingress, persistence, and the production container entrypoints they require.

### Modified Capabilities

None. No existing spec's requirements change.

## Impact

- **New files**: `service-compose.yml`, `backend/deploy/entrypoint.sh`.
- **Modified**: `backend/Dockerfile`, `frontend/Dockerfile` (add stages; existing behaviour
  becomes the `dev` stage), `docker-compose.yml` (add `target: dev`),
  `backend/requirements.txt`, `backend/config/settings.py` (static files),
  `frontend/next.config.ts` (admin rewrites), `README.md`, `CLAUDE.md`.
- **Runtime dependencies**: an existing Swarm with a `public` overlay network and a Traefik
  instance using the `le` cert resolver, plus writable `/mnt/persist/blueskies/` on the
  target node. All are external and pre-existing.
- **Credentials are external Swarm secrets** (`blueskies_django_secret_key`,
  `blueskies_postgres_password`), consumed as `*_FILE` and expanded by the entrypoint. They
  must exist on the swarm before the first deploy. See the design's credentials decision.
- Local development is unaffected: `docker compose up --build` continues to build and run
  the `dev` stages exactly as today.
