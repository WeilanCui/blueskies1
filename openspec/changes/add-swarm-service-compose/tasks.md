## 1. Backend production readiness

- [ ] 1.1 Add `gunicorn` and `whitenoise` to `backend/requirements.txt`
- [ ] 1.2 Add `whitenoise.middleware.WhiteNoiseMiddleware` to `MIDDLEWARE` in `settings.py`, directly after `SecurityMiddleware`
- [ ] 1.3 Set `STATIC_ROOT`, make `STATIC_URL` configurable via `DJANGO_STATIC_URL` (default unchanged), and add a `STORAGES` entry using WhiteNoise's compressed manifest storage
- [ ] 1.4 Add an optional `DJANGO_CACHE_URL` Redis cache backend, falling back to LocMemCache — DRF throttle counters are per-process otherwise and break across replicas
- [ ] 1.5 Confirm the existing discrete `POSTGRES_*` settings path is untouched, since the stack file supplies those variables

## 2. Container entrypoint

- [ ] 2.1 Create `backend/deploy/entrypoint.sh` (POSIX `sh`, `set -e`), ending in `exec "$@"` so `CMD` runs as PID 1 and signals propagate
- [ ] 2.2 Derive `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` and `DJANGO_CACHE_URL` from a single `REDIS_URL` when they are not already set, giving the result backend its own logical database
- [ ] 2.3 Handle `rediss://` broker URLs by appending `ssl_cert_reqs` if absent, since Celery refuses a TLS broker without it
- [ ] 2.4 Wait for TCP reachability of `POSTGRES_HOST:POSTGRES_PORT` before exec'ing, with a bounded timeout that fails loudly rather than hanging forever
- [ ] 2.5 Make the script executable and verify it is a no-op when every variable is already set

## 3. Dockerfile stages

- [ ] 3.1 Split `backend/Dockerfile` into `base` (system deps + pip install) → `dev` and `prod`, preserving current behaviour exactly in `dev`
- [ ] 3.2 In backend `prod`: copy source, run `collectstatic --noinput` at build time, set `ENTRYPOINT` to the entrypoint script and `CMD` to gunicorn bound on `0.0.0.0:8000`
- [ ] 3.3 Split `frontend/Dockerfile` into `deps` → `dev` and `builder` → `prod`, preserving current behaviour exactly in `dev`
- [ ] 3.4 In frontend `builder`: declare `ARG SERVER_API_BASE_URL`, promote it to `ENV` before `npm run build` so `next.config.ts` rewrites resolve at build time
- [ ] 3.5 In frontend `prod`: start from a clean slim base, install `curl` for the healthcheck, copy only `.next/standalone`, set `CMD ["node", "server.js"]`
- [ ] 3.6 Add `backend/.dockerignore` excluding `.venv`, caches, `staticfiles`, `celerybeat-schedule`, and `.git`
- [ ] 3.7 Add `target: dev` to every built service in `docker-compose.yml` so local development does not silently switch to the production stage

## 4. Frontend admin proxying

- [ ] 4.1 Add `rewrites()` to `frontend/next.config.ts` mapping `/admin` and `/admin/:path*` to the backend, re-appending the trailing slash Next strips so Django's `APPEND_SLASH` does not loop
- [ ] 4.2 Add a `/django-static/:path*` rewrite so admin assets resolve
- [ ] 4.3 Comment that `rewrites()` is evaluated at build time and therefore depends on the build argument from 3.4

## 5. The stack file

- [ ] 5.1 Create `service-compose.yml` with a `version:` string, `networks:` declaring `public` as `external: true` and a private `blueskies` overlay with `driver_opts: encrypted: "true"`
- [ ] 5.2 Add the `web` service: frontend image from `direct:5000`, on both networks, `deploy.labels` with the four standard Traefik openers plus router `blueskies-https` on entrypoint `https`, `certresolver=le`, host rule `blueskies1.tempestnetworks.net`, and loadbalancer server port
- [ ] 5.3 Add the `backend` service: backend image, private network only, `endpoint_mode: dnsrr`, environment for Postgres, Django hosts/CSRF/cookies and `REDIS_URL`
- [ ] 5.4 Add `celery` and `celery-beat` services sharing the backend image, overriding `command:` only
- [ ] 5.5 Add `db` (`postgres:16-alpine`) and `redis` (`redis:7-alpine`) with bind mounts under `/mnt/persist/blueskies/` and placement constraints pinning them to the node holding that data
- [ ] 5.6 Give every service a `deploy.resources` block with quoted `cpus:` and `M`-suffixed `memory:` limits and reservations, sized per role
- [ ] 5.7 Give every service a healthcheck in the house shape (`15s`/`15s`/`5`, with a `start_period` suited to its startup cost)
- [ ] 5.8 Add the standard three-line `net.ipv4.tcp_keepalive_*` `sysctls:` block
- [ ] 5.9 Verify no Swarm-ignored keys remain: no `build:`, no `depends_on:`, no `profiles:`, no `ports:` on private services

## 6. Documentation

- [ ] 6.1 Add a deployment section to `README.md`: build and push with `make push`, create the persist directories, `docker stack deploy`, then run migrations
- [ ] 6.2 Document that management commands must be run as `/app/deploy/entrypoint.sh python manage.py ...`, since `docker exec` bypasses the entrypoint
- [ ] 6.3 Document that `SERVER_API_BASE_URL` is baked into the frontend image at build time, so changing the backend address requires a rebuild rather than a redeploy
- [ ] 6.4 State plainly that `service-compose.yml` holds credentials in plaintext, that production values must not be committed, and record the `env_file` and Swarm-secrets migration paths
- [ ] 6.5 Add a "Deployment" section to `CLAUDE.md` listing what to preserve when editing this area: keep `dev` stages in sync, the build-time rewrite dependency, and the entrypoint bypass

## 7. Verification

- [ ] 7.1 `docker compose config` and `docker compose --profile frontend config` both resolve `target: dev` on every built service
- [ ] 7.2 `docker compose up --build` still starts the dev stack with hot reload and source bind-mounts working
- [ ] 7.3 `make build` produces both production images; confirm the backend image's `CMD` is gunicorn behind the entrypoint, and the frontend image contains `server.js` and `curl`
- [ ] 7.4 Confirm `collectstatic` ran in the backend image by listing `staticfiles/admin` inside it
- [ ] 7.5 Validate the stack file parses: `docker stack config -c service-compose.yml` succeeds and shows no ignored-key warnings
- [ ] 7.6 Run the entrypoint in isolation with only `REDIS_URL` set; confirm it derives all three URLs and that the result backend uses a different logical database
- [ ] 7.7 Confirm the entrypoint's database wait fails loudly on an unreachable host rather than hanging
- [ ] 7.8 Deploy the stack to the Swarm; confirm all six services converge to running and pass their healthchecks
- [ ] 7.9 Run `migrate` and `createsuperuser` through the entrypoint; confirm both succeed
- [ ] 7.10 Confirm `https://blueskies1.tempestnetworks.net/` serves the app over TLS with a valid certificate
- [ ] 7.11 Confirm `/admin` loads **styled** (assets resolve via `/django-static/`) and does not redirect-loop — the trailing-slash regression manifests only here
- [ ] 7.12 Confirm an app API route works end to end, proving the Next → Django private-network proxy path
- [ ] 7.13 Confirm Django, Celery, Postgres and Redis are NOT reachable from outside the Swarm
- [ ] 7.14 Confirm a Celery task runs, and that beat schedules its nightly job
- [ ] 7.15 Redeploy the stack and confirm Postgres data survives
