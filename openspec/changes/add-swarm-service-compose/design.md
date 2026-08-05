## Context

`docker-compose.yml` is development-only. The `Makefile` publishes images to `direct:5000`.
Nothing connects the two: there is no stack file, and the images are not independently
runnable — neither Dockerfile declares a `CMD`, so the command has always come from compose.

The target Swarm already runs 23 stacks under `~/workspace/tempest/docker/`, and this file
should read like a sibling of those. The conventions observed there and adopted here:

- One file per stack, `<stack>-compose.yml`, with a `version:` string and no header comment.
- `deploy:` key order `mode` → `replicas` → `endpoint_mode` → `resources` → `placement`,
  `endpoint_mode: dnsrr` on every service Traefik does not load-balance, quoted `cpus:`
  values, unquoted `memory:` with an `M` suffix.
- `public` declared `external: true`; one private overlay per stack with
  `driver_opts: encrypted: "true"`.
- Persistence via host bind mounts under `/mnt/persist/<stack>/`, not named volumes.
- Healthchecks shaped `interval: 15s` / `timeout: 15s` / `retries: 5` / `start_period: 10s`.
- Traefik labels under `deploy.labels`, opening with the same four keys, router named
  `<name>-https`, `certresolver=le`.
- The three-line `net.ipv4.tcp_keepalive_*` `sysctls:` block on most services.
- No `secrets:` anywhere; credentials sit inline in `environment:`. (This stack departs
  from that one convention — see the credentials decision below.)

## Goals / Non-Goals

**Goals:**

- A stack file that deploys as-is and reads as a sibling of the existing tempest stacks.
- Production images that run unattended, with no command supplied by the orchestrator.
- Exactly one externally reachable service.
- Local development behaviour preserved bit-for-bit.

**Non-Goals:**

- Changing how the frontend talks to the backend. `lib/backendProxy.ts` and the `app/api/`
  route handlers already proxy server-side; that is what makes a single public service possible.
- CI/CD, automated deploys, or blue/green rollout. Deployment stays a manual
  `docker stack deploy`.
- Multi-node scale-out of Postgres or Redis. Both are single-replica and node-pinned.
- Migrating the tempest stacks to a different secret-handling model.
- Sablier scale-to-zero. Available in the house style, but a cold start on every first
  request is the wrong trade for an app with background Celery work.

## Decisions

### `web` is the only public service

The Swarm's Traefik keys routers on hostname, and the browser never calls Django directly —
every client request already goes through a Next.js route handler that proxies via
`lib/backendProxy.ts` at `SERVER_API_BASE_URL`. So Django can sit entirely on the private
overlay with no frontend changes. Public hostname: `blueskies1.tempestnetworks.net`.

The one exception is the Django admin, which is served by Django itself rather than through
`app/api/`. It is reached via `next.config.ts` rewrites for `/admin` and `/django-static`.
Two details make this work: Next evaluates `rewrites()` at **build** time and bakes the
destination into the route manifest, so `SERVER_API_BASE_URL` must be a **build argument**
to the frontend image, not just a runtime env var; and the rewrite destinations must
re-append the trailing slash Next strips, or Django's `APPEND_SLASH` redirects back and the
two loop.

*Alternative considered:* a second Traefik router sending `/admin` straight to Django.
Rejected — it needs Django on the `public` network, which defeats the single-ingress goal
for a path used a few times a month.

### Credentials as external Swarm secrets

The stack originally followed the tempest house style — values inline in `environment:` —
and that shipped briefly. It was wrong for a repository with a remote: anyone who could read
the repo could read the database password and forge sessions with the Django secret key, and
git history makes that permanent. The credentials are now `external: true` Swarm secrets
(`blueskies_django_secret_key`, `blueskies_postgres_password`), created with
`docker secret create` and mounted at `/run/secrets/`; the stack file carries only the names.
The values committed earlier must be treated as burned and rotated.

`external: true` rather than a stack-defined secret because a stack-defined one still needs
its value from a file at deploy time, which puts it back into the operator's tree.
API-key slots (`OPENAI_API_KEY`, `NCBI_API_KEY`) stay as empty `environment:` entries: there
is nothing to protect yet, and the `_FILE` mechanism below covers them unchanged when there is.

### An entrypoint, for startup ordering and secret expansion

`backend/deploy/entrypoint.sh` earns its place doing three jobs:

- **Expand `FOO_FILE` into `FOO`.** Swarm presents a secret as a file; Django reads
  environment variables. One generic loop bridges the two for every variable, so adding a
  secret is a stack-file change only. An explicitly set `FOO` wins, leaving compose untouched.
- **Derive the Celery URLs from one `REDIS_URL`.** Otherwise the same host and port are
  repeated across three variables on three services, and they drift. The script also gives
  the result backend its own logical database, and handles `rediss://` needing an explicit
  `ssl_cert_reqs`.
- **Wait for Postgres before exec'ing.** Swarm has no `depends_on`; without this, backend,
  worker and beat all crash-loop through their restart policy until the database is up.
  Noisy, and slow to converge. The probe opens a real `psycopg` connection rather than a TCP
  socket, because Postgres accepts connections on the port before it will serve SQL, and it
  is bounded by a wall-clock deadline so the probe's own timeout cannot double the wait.

It ends in `exec "$@"`, so the container's `CMD` is still what runs and signals propagate
correctly. Note that `docker exec` bypasses an entrypoint, so
management commands must be run as `/app/deploy/entrypoint.sh python manage.py ...`.

### Migrations run automatically, on the Django service only

The entrypoint runs `migrate` when `DJANGO_MIGRATE_ON_START` is set, and the stack file
sets it **only on the `backend` service**. Celery worker and beat share the same image and
the same entrypoint, so without that gate all three would migrate concurrently on every
deploy and race each other.

The services that do **not** migrate do not simply proceed: they block on
`manage.py migrate --check` until the Django service has finished. Swarm starts all four at
once, so without that barrier a worker can pull queued tasks and execute them against the
previous schema for as long as `backend` takes to migrate. `MIGRATION_WAIT_SECONDS` bounds
the wait; exceeding it fails the task, and `restart_policy: on-failure` retries.

The gate is an explicit environment variable rather than the entrypoint inspecting `$@` to
guess whether it is about to run gunicorn. Sniffing the command couples the entrypoint to
the exact `CMD` strings, and fails silently the first time one is reworded — a silent
failure to migrate is far worse than a loud one.

This makes `backend` single-replica a correctness requirement, not just a sizing choice:
Django takes no global migration lock, so two replicas starting together would race the
same way the three services would. The stack file pins `replicas: 1` and the design records
why. Scaling the web tier later means moving migration to a one-shot service run before the
rollout, not raising the replica count.

Migration still runs after the database wait and before `exec "$@"`, so a failed migration
fails the task and Swarm surfaces it, rather than serving traffic against a stale schema.

*Alternative considered:* leave migration entirely to the operator as a documented
post-deploy step. Safer for rollback — an automatic migration on deploy means rolling the
image back does not roll the schema back — but it makes every deploy a two-step manual
process and a forgotten step yields confusing runtime errors. The rollback caveat is
recorded under Risks instead.

### Multi-stage Dockerfiles with the dev stage preserved

`backend`: `base` (dependencies) → `dev` | `prod`. `frontend`: `deps` → `dev` | `builder`
→ `prod`, where `prod` is a fresh slim image carrying only `.next/standalone`. This keeps
the production image small and free of build toolchain.

`docker-compose.yml` gains `target: dev` on every built service. Without it, compose would
build the *last* stage — production — and silently change local development. The `dev`
stages must be kept in sync when dependencies change.

### Static files via WhiteNoise

The admin needs CSS. `settings.py` gains `STATIC_ROOT` and a WhiteNoise storage backend,
`requirements.txt` gains `whitenoise` and `gunicorn`, and the backend `prod` stage runs
`collectstatic` at build time. `STATIC_URL` becomes configurable and is set to
`/django-static/` in production so the prefix does not collide with Next's own asset routes.

*Alternative considered:* serve static from Traefik or a sidecar. Rejected as far more
moving parts for a handful of admin assets.

### Postgres and Redis in-stack, on bind mounts

Both run as single-replica services with `/mnt/persist/blueskies/postgres` and
`/mnt/persist/blueskies/redis` bind-mounted, matching the dominant tempest idiom, and each
pinned by a placement constraint to the node holding that data. This keeps the stack
self-contained and independently deployable.

## Risks / Trade-offs

- **Credentials committed in an earlier revision of this branch** → Permanent in git
  history. Both values are rotated and the stack now reads external Swarm secrets; nothing
  sensitive remains in the file.
- **Bind mounts pin datastores to one node** → Deliberate: placement constraints make it
  explicit rather than accidental. A node loss requires restoring the path.
- **`SERVER_API_BASE_URL` is baked into the frontend image at build time** → A different
  backend address requires a rebuild, not just a redeploy. Inherent to Next's rewrite
  handling; called out in the README so it is not discovered during an incident.
- **Three backend services race to be ready before Postgres** → Mitigated by the entrypoint
  wait rather than by restart-loop convergence.
- **Automatic migration means an image rollback does not roll the schema back** → Inherent
  to migrate-on-deploy. Reversible migrations and checking the diff before deploying remain
  the operator's job; the alternative (manual migration) was weighed and rejected above.
- **`backend` must stay at one replica or concurrent migrations race** → Pinned in the
  stack file and stated in the design; scaling requires moving migration to a one-shot
  service first, not editing `replicas`.
- **Compose would build the production stage by default** → Mitigated by pinning
  `target: dev`. If a future stage is appended, that pin is what keeps local dev correct.
- **The admin path depends on a rewrite whose trailing-slash handling is subtle** → Covered
  by an explicit verification step, since a regression here manifests as a redirect loop
  rather than an obvious error.

## Migration Plan

Additive; no existing deployment to migrate. Order: build and push images with the
`Makefile`, ensure `/mnt/persist/blueskies/{postgres,redis}` exist on the target node, then
`docker stack deploy -c service-compose.yml blueskies1`. The backend applies migrations
itself on start; only `createsuperuser` is a manual one-off, run via the entrypoint.
Rollback is `docker stack rm blueskies1` — note that this does not unapply migrations; the
bind-mounted data survives, and local development is untouched throughout.

## Open Questions

- Which node should carry the datastore constraint. The tempest stacks use
  `node.labels.name == direct` and `node.labels.data==true`; this design assumes a label
  exists and leaves the exact value to be set at deploy time.
- Whether Celery beat's schedule file needs its own persistent path. It currently writes
  `celerybeat-schedule` into the working directory, which is now gitignored but still
  container-local and lost on restart.
