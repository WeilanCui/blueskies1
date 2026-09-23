# Blueskies

Blueskies is a skincare intelligence app in progress. The product vision is to
help people understand their skin, capture their current regimen, scan products,
track skin changes over time, and connect those changes to ingredients,
formulations, weather/location, hormone cycle context, and product history.

The app is currently a prototype and roadmap build, not a fully working consumer
product.

## What It Shows Today

- A roadmap landing page for users and investors at `/`
- A landing-page early access form that emails a Mailgun verification code
  before marking the submission verified for admin follow-up
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

For landing-page email verification, set the Mailgun values in `.env`:
`MAILGUN_API_KEY`, `MAILGUN_DOMAIN`, `MAILGUN_FROM_EMAIL`,
`MAILGUN_API_BASE`, and `CONTACT_VERIFICATION_SECRET`.
Verified beta emails can then create an account at `/login?mode=signup`;
after signup, incomplete profiles continue to `/intake`.

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

Both Dockerfiles are multi-stage, and `BACKEND_TARGET`/`FRONTEND_TARGET` default to
`prod`. The stage is named explicitly rather than left to the last-stage-wins default, so
appending a stage cannot silently change what ships. `make build BACKEND_TARGET=dev`
publishes a development image for debugging.

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
overlay, so Django never needs to be exposed. Traefik routes three hostnames to it over
TLS (`blueskies1.tempestnetworks.net`, `cereneskin.com` and `mymoondrip.com`) as three
routers onto the same `blueskies` service. All three must appear in `DJANGO_ALLOWED_HOSTS`
and in the CSRF/CORS origin lists.

### Deploying

```bash
# On the node matching the placement constraint, once. Swarm does NOT create bind
# sources the way `docker run` does -- without these the db/redis/beat tasks are
# rejected with "bind source path does not exist".
sudo mkdir -p /mnt/persist/blueskies/{postgres,redis,beat}
# The backend image runs as uid 10001, which must own the beat schedule directory.
sudo chown 10001:10001 /mnt/persist/blueskies/beat

# Once per swarm, before the first deploy -- see "Credentials" below.
openssl rand -base64 48 | docker secret create blueskies_django_secret_key -
openssl rand -base64 24 | docker secret create blueskies_postgres_password -

make release        # build + push + deploy, from a swarm manager
make deploy-status  # services and any task errors
```

`release` is `push` followed by `deploy TAG=<revision>`, so the running stack always names
the commit it was built from (`-dirty` when built from uncommitted work). The two halves
are also separate targets, because they are needed independently:

```bash
make deploy   # redeploy after editing service-compose.yml only -- no rebuild, TAG=latest
make push     # publish images without touching the running stack
```

The stack file's image references are `${REGISTRY:-direct:5000}/${PROJECT:-blueskies}-*`
`:${TAG:-latest}`, and the Makefile exports those three variables, so overriding
`REGISTRY` or `PROJECT` moves both the push and the deploy together. `docker service
inspect --format '{{.Spec.TaskTemplate.ContainerSpec.Image}}' blueskies1_web` reports which
revision is live.

`STACK` (default `blueskies1`) and `STACK_FILE` (default `service-compose.yml`) are
overridable, so a second environment is `make release STACK=blueskies-staging`.

Expect the backend to fail its first attempt or two while Postgres is still being
scheduled: the entrypoint waits 60s for the database to accept a real connection, then
exits, and the restart policy retries. This is self-correcting — `POSTGRES_WAIT_SECONDS`
raises the window if your scheduler is slower than that.

### TLS certificates

Traefik does not request certificates itself, and the routers in `service-compose.yml`
set `tls=true` with no `tls.certresolver`. Certificates come from the separate
`traefik-acme` stack:

- `traefik-acme_issuer` is a single replica that obtains every certificate listed in the
  inventory (the `traefik-acme_traefik_acme_inventory_*` Swarm config) and publishes each
  one as an immutable bundle under `/mnt/persist/traefik-acme/published`.
- `traefik-acme_cert-sync` runs once per manager and writes the current bundle into the
  Traefik file provider directory on that node, so every edge replica serves the same
  certificate.
- `traefik-acme_challenge` runs once per manager and answers
  `/.well-known/acme-challenge/` on port 80 from the issuer's shared webroot.

Before, three Traefik replicas each ran ACME and raced each other for the same challenge,
which left the losers holding no certificate until a forced restart. That failure mode is
gone, and adding a hostname no longer needs `docker service update --force
traefik_traefik`.

`blueskies1.tempestnetworks.net` is covered by the `*.tempestnetworks.net` wildcard, which
the issuer obtains with Cloudflare DNS-01. `cereneskin.com` and `mymoondrip.com` sit in a
different Cloudflare account that the issuer's API token cannot see, so they use HTTP-01
through the challenge service instead. That needs port 80 on the managers to reach
`traefik-acme_challenge` for `/.well-known/acme-challenge/`.

#### Adding a hostname

1. Add the name to the certificate inventory in the `traefik-acme` stack and redeploy that
   stack, so the issuer obtains the certificate and cert-sync activates it on every
   manager. Do this first: a router deployed before its certificate exists answers the
   handshake with a TLS `unrecognized_name` alert.
2. Add a router to `web` in `service-compose.yml` with `tls=true`, no `certresolver`, and
   an explicit `.service=blueskies` (required once more than one router points at the
   service). Add the host to `DJANGO_ALLOWED_HOSTS` and the CSRF/CORS origin lists.
3. `make deploy`.

Check every manager directly rather than through Cloudflare, which hides which edge
answered:

```bash
for ip in <manager-ips>; do
  for host in blueskies1.tempestnetworks.net cereneskin.com mymoondrip.com; do
    out=$(echo | timeout 5 openssl s_client -connect "$ip:443" -servername "$host" \
      2>&1 | grep -m1 -E 'subject=|unrecognized')
    printf '%s %s: %s\n' "$ip" "$host" "${out:-FAILED: no certificate or no handshake}"
  done
done
```

Add any new hostname to the inner loop. Every manager should print the expected subject
for every host:

| Host | Expected subject |
| --- | --- |
| `blueskies1.tempestnetworks.net` | `CN = *.tempestnetworks.net` |
| `cereneskin.com` | `CN = cereneskin.com` |
| `mymoondrip.com` | `CN = mymoondrip.com` |

A line containing `unrecognized` means that edge has no certificate for the host yet. A
`FAILED` line means the handshake did not complete at all (edge unreachable, connection
refused, or timed out); check that edge by hand with the same `openssl s_client` command.

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
- **A long migration will not be killed by the healthcheck.** The entrypoint holds
  `/tmp/entrypoint-migrating` while `migrate` runs and the `backend` check treats that as
  healthy, because no fixed `start_period` can bound an arbitrary migration. A migration
  blocked on someone else's lock still fails fast: it runs with
  `lock_timeout=$DJANGO_MIGRATE_LOCK_TIMEOUT` (default 30s), so the task exits and retries
  rather than sitting healthy forever. `statement_timeout` is deliberately left off, so a
  slow-but-progressing data migration runs to completion.
- **`SERVER_API_BASE_URL` is baked into the frontend image at build time.** Next resolves
  `rewrites()` during `next build` and writes the destinations into the route manifest.
  Changing the backend address therefore needs a rebuild and re-push, not just a redeploy.
- **`celery` and `celery-beat` deliberately do not set `DJANGO_MIGRATE_ON_START`.** They
  share the backend image, and would otherwise all migrate concurrently on every deploy.
  Instead the entrypoint blocks them on `migrate --check` until `backend` has finished, so
  a worker never consumes queued tasks against the previous schema. `MIGRATION_WAIT_SECONDS`
  (default 300) bounds that wait; exceeding it fails the task and the restart policy retries.
- **`db`, `redis` and `celery-beat` are pinned by placement constraint** to the node holding
  their data under `/mnt/persist/blueskies/`. Adjust the `node.labels.name` constraint to
  match your swarm.

### Credentials

The Django secret key and the Postgres password are **Swarm secrets**, declared
`external: true` so their values exist only on the swarm:

```bash
openssl rand -base64 48 | docker secret create blueskies_django_secret_key -
openssl rand -base64 24 | docker secret create blueskies_postgres_password -
```

Services mount them at `/run/secrets/<name>` and reference them as `DJANGO_SECRET_KEY_FILE`
and `POSTGRES_PASSWORD_FILE`. `backend/deploy/entrypoint.sh` expands **any** `FOO_FILE` into
`FOO` before starting the process, so `OPENAI_API_KEY` and `NCBI_API_KEY` follow the same
path once they stop being empty — add a secret and swap the variable for its `_FILE` form.
The `postgres` image reads `POSTGRES_PASSWORD_FILE` natively, and `settings.py` reads the
`_FILE` form of `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD` itself — necessary because a
container healthcheck and `docker exec` start from the container's configured environment
and never see the entrypoint's exports. An explicitly set `FOO` always wins over `FOO_FILE`,
which is why local `docker compose` development is unaffected.

Rotating a secret Swarm cannot update in place (a secret's contents are immutable):

```bash
# 1. The postgres image sets the role's password only when it initialises an empty
#    data directory, so an existing deployment must be told directly.
docker exec -it $(docker ps -qf name=blueskies1_db) \
  psql -U blueskies -d blueskies -c "ALTER ROLE blueskies WITH PASSWORD '<new>';"

# 2. Replace the secret under a new name, point the stack file at it, redeploy.
printf '%s' '<new>' | docker secret create blueskies_postgres_password_v2 -
```

**Earlier revisions of this repository committed the live secret key and database password
in plaintext.** Git history is permanent, so both values must be treated as compromised and
rotated — the key rotation invalidates every existing session, which is expected.

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
- `ContactSubmission` records from the landing-page form, including Mailgun
  email verification state, visible in Django admin

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
