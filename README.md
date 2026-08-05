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

Start the backend stack:

```bash
docker compose up --build
```

This starts Postgres, Redis, Django, the Celery worker, and Celery beat. The
frontend container is opt-in so everyday frontend work can run through Next.js
dev mode with hot reload.

Open:

- Backend health check: http://localhost:8000/api/health/

Run the frontend directly:

```bash
cd frontend
npm install
npm run dev
```

If port `3000` is occupied, Next.js will use the next available port.

You can also run the frontend in Docker dev mode:

```bash
docker compose --profile frontend up --build frontend
```

The frontend container installs its npm dependencies before starting, so rebuilt
images and reused compose volumes stay in sync with `frontend/package-lock.json`.

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

Lint the frontend:

```bash
cd frontend
npm run lint
```

Biome is configured in `frontend/biome.json` and scoped to `app/`, `components/`, `hooks/`, and `lib/`.

## Building and Publishing Images

The root `Makefile` builds each service's image and pushes it to the local registry at
`direct:5000`. This is separate from local development — `docker compose up --build`
builds its own images and is unaffected.

```bash
make            # list targets and the current variable values
make build      # build both images
make push       # build and push both images
make clean      # remove the locally built tags
```

Per-service targets exist too: `build-backend`, `push-frontend`, and so on. The backend
image serves `backend`, `celery`, and `celery-beat` — they share a build context and
differ only in their command.

Each image is tagged twice: a mutable `latest` and the abbreviated commit hash, so a
deployed image can always be traced back to a commit. Building from a working tree with
uncommitted changes appends `-dirty` to the hash, so such an image can never be mistaken
for a clean commit's. Deployments should reference the hash tag, not `latest`.

Every input is overridable on the command line:

```bash
make push TAG=v1.2.3
make build REGISTRY=localhost:5000 PLATFORM=linux/amd64
make push BUILD_ARGS='--build-arg SERVER_API_BASE_URL=http://backend:8000'
```

`REGISTRY`, `PROJECT`, `TAG`, `DOCKER`, `PLATFORM`, `BUILD_ARGS`, `BACKEND_TARGET`, and
`FRONTEND_TARGET` are all supported; `make help` prints their current values.

Both Dockerfiles are currently single-stage, so no `--target` is passed. If they gain
named stages, select one explicitly with `make build BACKEND_TARGET=prod` rather than
relying on the last stage winning — otherwise appending a stage silently changes what
gets published.

### Registry prerequisites

`direct:5000` is a plain-HTTP registry, so two things must be true on the build host
before `make push` will work. The Makefile does not configure either — both are
root-owned host changes.

1. **`direct` must resolve.** Check with `getent hosts direct`. Add it to `/etc/hosts` or
   your DNS if it does not, or override with `make push REGISTRY=<ip>:5000`.
2. **The Docker daemon must accept the insecure registry.** Without this, the push fails
   with `http: server gave HTTP response to HTTPS client`. Add it to
   `/etc/docker/daemon.json` and restart the daemon:

   ```json
   { "insecure-registries": ["direct:5000"] }
   ```

   ```bash
   sudo systemctl restart docker
   ```

Confirm the registry is reachable before pushing, and inspect what landed afterwards:

```bash
curl -s http://direct:5000/v2/_catalog
curl -s http://direct:5000/v2/blueskies-backend/tags/list
```

## Deploying to Docker Swarm

`service-compose.yml` is the Swarm stack file. It runs six services: `web` (Next.js),
`backend` (Django under gunicorn), `celery`, `celery-beat`, `db`, and `redis`.

**`web` is the only service reachable from outside the swarm.** The browser already talks
only to the Next.js route handlers in `app/api/`, which proxy to Django over the private
overlay, so Django never needs to be exposed. Traefik routes
`blueskies1.tempestnetworks.net` to it over TLS.

### Deploying

```bash
make push BUILD_ARGS='--build-arg SERVER_API_BASE_URL=http://backend:8000' \
          BACKEND_TARGET=prod FRONTEND_TARGET=prod

# On the node matching the placement constraint, once. Swarm does NOT create bind
# sources the way `docker run` does -- without these the db/redis/beat tasks are
# rejected with "bind source path does not exist".
sudo mkdir -p /mnt/persist/blueskies/{postgres,redis,beat}

docker stack deploy -c service-compose.yml blueskies1
docker stack services blueskies1
```

Expect the backend to fail its first attempt or two while Postgres is still being
scheduled: the entrypoint waits 60s for the database, then exits, and the restart policy
retries. This is self-correcting — `POSTGRES_WAIT_SECONDS` raises the window if your
scheduler is slower than that.

### After adding a hostname, restart Traefik

```bash
docker service update --force traefik_traefik
```

Traefik runs three replicas, which all race to solve the same ACME challenge. One wins and
writes the certificate to the shared store; the others fail with
`400 malformed :: authorization must be pending` and hold **no certificate in memory**.
Traefik does not reload another process's writes to that store, so those replicas answer
the new hostname with a TLS `unrecognized_name` alert — `ERR_SSL_UNRECOGNIZED_NAME_ALERT`
in the browser — until they are restarted. The rolling restart is safe; the certificate is
already in the shared store, so no new ACME request is made.

This is deceptive to diagnose, because a request through Cloudflare can land on the one
healthy replica and look completely fine. Check each origin directly instead:

```bash
for ip in <manager-ips>; do
  echo | openssl s_client -connect "$ip:443" -servername blueskies1.tempestnetworks.net \
    2>&1 | grep -E 'subject=|unrecognized'
done
```

Every replica should print `subject=CN = blueskies1.tempestnetworks.net`. Any that print
`unrecognized name` still need the restart.

Migrations apply themselves: the backend container runs `migrate` on startup, before it
begins serving. Only `createsuperuser` is a manual step.

### Operating it

Management commands must go through the entrypoint, because `docker exec` bypasses it and
none of the Redis derivation will have happened:

```bash
docker exec -it -e DJANGO_MIGRATE_ON_START= $(docker ps -qf name=blueskies1_backend) \
  /app/deploy/entrypoint.sh python manage.py createsuperuser
```

`docker exec` inherits the container's environment, so without blanking
`DJANGO_MIGRATE_ON_START` every management command re-runs `migrate` first. That is
idempotent and harmless, just noisy.

Things that will bite you if you don't know them:

- **`backend` must stay at `replicas: 1`** while migrations run from the entrypoint. Django
  takes no global migration lock, so two replicas starting together race each other.
  Scaling the Django tier means moving migration to a one-shot service first — not raising
  the replica count.
- **An image rollback does not roll back applied migrations.** Write migrations reversibly.
- **`SERVER_API_BASE_URL` is baked into the frontend image at build time.** Next resolves
  `rewrites()` during `next build` and writes the destinations into the route manifest.
  Changing the backend address therefore needs a rebuild and re-push, not just a redeploy.
- **`celery` and `celery-beat` deliberately do not set `DJANGO_MIGRATE_ON_START`.** They
  share the backend image, and would otherwise all migrate concurrently on every deploy.
- **`db`, `redis` and `celery-beat` are pinned by placement constraint** to the node holding
  their data under `/mnt/persist/blueskies/`. Adjust the `node.labels.name` constraint to
  match your swarm.

### Credentials

`service-compose.yml` holds its credentials in **plaintext**, matching the convention of
the other stacks on this swarm. Anyone who can read the repo or run `docker stack config`
can read the database password and the API keys.

The checked-in values are the ones currently deployed, committed deliberately while this
is a prototype. **They must be rolled before this serves real users**, and at that point
the credentials should move out of the file entirely. Two ways to do that without
restructuring it:

- Move the sensitive subset into an `env_file:` on a host path under
  `/mnt/persist/blueskies/config/`, as the keycloak and grafana stacks do.
- Adopt Swarm `secrets:`. `backend/deploy/entrypoint.sh` is already shaped for this — it
  exports derived values before `exec`, so reading `*_FILE` secrets is a small edit to one
  script rather than a change to every service definition.

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

The `pyright` hook runs on every commit, configured via `pyrightconfig.json` at standard type-checking mode scoped to the `backend/` directory. Django-aware typing comes from `django-types` and `djangorestframework-stubs`. A handful of standard-mode diagnostics are downgraded to warnings where they fire on framework/stub limitations (e.g. reverse-relation accessors, abstract-model `Meta`); each downgrade is documented inline in `pyrightconfig.json`.

Note: the hook resolves imports from your installed environment, so install `backend/requirements-dev.txt` (which pulls in the runtime deps) before committing — otherwise pyright reports unresolved third-party imports. `pyrightconfig.json` sets `venvPath`/`venv` to `./.venv`, the layout `.gitignore` already assumes, so a repo-root virtualenv is picked up whether or not it is activated. Resolution order:

1. `./.venv`, if it exists — this takes priority over an activated virtualenv, so a stale `./.venv` will shadow the environment you think you are using. Delete it, or point it at the right place.
2. Otherwise pyright prints one "subdirectory not found" notice and falls back to the `python` on your PATH, which is what an activated virtualenv or a global install gives you.

If you keep your virtualenv somewhere else and do not want to move it, symlink it — `.venv` is gitignored, so this stays local to your checkout:

```bash
ln -s /path/to/your/venv .venv
```

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
