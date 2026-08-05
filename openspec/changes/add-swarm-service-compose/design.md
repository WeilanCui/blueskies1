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
- No `secrets:` anywhere; credentials sit inline in `environment:`.

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

### Plaintext credentials in `environment:`, matching the neighbours

Per direction, this stack follows the tempest house style: no `secrets:`, values inline.

**This is a deliberate trade-off with a real cost, recorded here so it is not mistaken for
an oversight.** Anyone who can run `docker stack config`, read the repo, or inspect the
service definition can read the database password and the OpenAI and NCBI API keys. The
file must therefore never carry production credentials into a public remote. Two mitigations
are available later without restructuring: move the sensitive subset into an `env_file:`
under `/mnt/persist/blueskies/config/`, as the keycloak and grafana stacks do, or adopt
Swarm `secrets:` — the entrypoint below is already shaped to make that a small change.

### An entrypoint, but for startup ordering rather than secrets

The direction selected an entrypoint script alongside plaintext env. With no secret files to
bridge, `backend/deploy/entrypoint.sh` earns its place doing two other jobs:

- **Derive the Celery URLs from one `REDIS_URL`.** Otherwise the same host and port are
  repeated across three variables on three services, and they drift. The script also gives
  the result backend its own logical database, and handles `rediss://` needing an explicit
  `ssl_cert_reqs`.
- **Wait for Postgres before exec'ing.** Swarm has no `depends_on`; without this, backend,
  worker and beat all crash-loop through their restart policy until the database is up.
  Noisy, and slow to converge.

It ends in `exec "$@"`, so the container's `CMD` is still what runs and signals propagate
correctly. Keeping the file means adopting Swarm secrets later is an edit to one script
rather than a change of shape. Note that `docker exec` bypasses an entrypoint, so
management commands must be run as `/app/deploy/entrypoint.sh python manage.py ...`.

### Migrations are operator-run, not automatic

The entrypoint waits for the database but does **not** run `migrate`. Three backend
services start concurrently; migrating from all of them races, and an automatic migration
on deploy makes rollback unsafe. Documented as a deliberate post-deploy step.

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

- **Credentials readable by anyone with Swarm or repo access** → Accepted per direction and
  documented above; two migration paths recorded. Do not commit production values.
- **Bind mounts pin datastores to one node** → Deliberate: placement constraints make it
  explicit rather than accidental. A node loss requires restoring the path.
- **`SERVER_API_BASE_URL` is baked into the frontend image at build time** → A different
  backend address requires a rebuild, not just a redeploy. Inherent to Next's rewrite
  handling; called out in the README so it is not discovered during an incident.
- **Three backend services race to be ready before Postgres** → Mitigated by the entrypoint
  wait rather than by restart-loop convergence.
- **Compose would build the production stage by default** → Mitigated by pinning
  `target: dev`. If a future stage is appended, that pin is what keeps local dev correct.
- **The admin path depends on a rewrite whose trailing-slash handling is subtle** → Covered
  by an explicit verification step, since a regression here manifests as a redirect loop
  rather than an obvious error.

## Migration Plan

Additive; no existing deployment to migrate. Order: build and push images with the
`Makefile`, ensure `/mnt/persist/blueskies/{postgres,redis}` exist on the target node,
`docker stack deploy -c service-compose.yml blueskies`, then run `migrate` and
`createsuperuser` once via the entrypoint. Rollback is `docker stack rm blueskies`; the
bind-mounted data survives, and local development is untouched throughout.

## Open Questions

- Which node should carry the datastore constraint. The tempest stacks use
  `node.labels.name == direct` and `node.labels.data==true`; this design assumes a label
  exists and leaves the exact value to be set at deploy time.
- Whether Celery beat's schedule file needs its own persistent path. It currently writes
  `celerybeat-schedule` into the working directory, which is now gitignored but still
  container-local and lost on restart.
