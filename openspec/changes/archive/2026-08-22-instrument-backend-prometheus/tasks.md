## 1. Dependencies & settings

- [x] 1.1 Add `django-prometheus>=2.3` to `backend/requirements.txt` (pulls `prometheus-client` transitively) and regenerate any lockfile the repo uses
- [x] 1.2 In `backend/config/settings.py`, add `PROMETHEUS_METRICS_ENABLED = env.bool("PROMETHEUS_METRICS_ENABLED", default=False)`, `PROMETHEUS_CELERY_WORKER_PORT = env.int(..., default=9808)`, `PROMETHEUS_CELERY_BEAT_PORT = env.int(..., default=9809)`, `PROMETHEUS_MULTIPROC_DIR = env("PROMETHEUS_MULTIPROC_DIR", default="/tmp/prometheus_multiproc")`
- [x] 1.3 Gate `INSTALLED_APPS` and `MIDDLEWARE` on `PROMETHEUS_METRICS_ENABLED`: append `"django_prometheus"` to apps, and wrap the existing middleware list with `django_prometheus.middleware.PrometheusBeforeMiddleware` (first) and `PrometheusAfterMiddleware` (last), preserving the existing relative order of the intervening middleware
- [x] 1.4 When the flag is on, switch `DATABASES["default"]["ENGINE"]` to `"django_prometheus.db.backends.postgresql"` and add the `django_prometheus` cache wrapper around the Redis cache backend used for throttles

## 2. Observability package

- [x] 2.1 Create `backend/core/observability/__init__.py`, `metrics.py`, `celery_metrics.py`, `bootstrap.py`
- [x] 2.2 In `metrics.py`, define the custom metric objects: `FORMULATION_INGEST_TOTAL` (Counter), `RECOMMENDATION_SCORE_SECONDS` (Histogram with buckets from design §5), `EXTERNAL_API_REQUEST_SECONDS` (Histogram with buckets from design §5). Every metric registered on the default registry; every Gauge added later MUST pass `multiprocess_mode=`
- [x] 2.3 In `metrics.py`, define `Literal`-typed constants for the allowed values of the `service` and `outcome` labels used by `EXTERNAL_API_REQUEST_SECONDS` and the `result` label used by `FORMULATION_INGEST_TOTAL`
- [x] 2.4 In `celery_metrics.py`, connect handlers for `task_prerun`, `task_postrun`, `task_success`, `task_failure`, `task_retry`; each handler wrapped in `try/except Exception: logger.exception(...)` so metrics bugs never fail tasks
- [x] 2.5 In `celery_metrics.py`, connect a `beat_init` handler and a per-tick handler that updates `celery_beat_last_tick_seconds` and `celery_beat_seconds_since_last_tick`
- [x] 2.6 In `bootstrap.py`, provide `enable_worker_metrics()` and `enable_beat_metrics()` that short-circuit when the flag is off, otherwise register signals and call `prometheus_client.start_http_server(port)` with the configured port

## 3. Celery wiring

- [x] 3.1 In `backend/config/celery.py`, import `bootstrap` and connect `celeryd_init.connect(lambda **_: bootstrap.enable_worker_metrics())` and `beat_init.connect(lambda **_: bootstrap.enable_beat_metrics())`
- [x] 3.2 Verify the worker still boots when the flag is `False` (no port binding, no signal receivers)

## 4. HTTP endpoint

- [x] 4.1 In `backend/config/urls.py` (or `core/urls.py` if that's where the existing `health/` path lives), conditionally include `path("metrics/", django_prometheus.exports.ExportToDjangoView, name="prometheus-metrics")` when the flag is on; when off, do not register the path so an unmatched `GET /metrics` returns Django's 404
- [x] 4.2 Confirm `/metrics` bypasses DRF authentication and throttling (it must not consume the `anon` throttle bucket)

## 5. Domain hot-path instrumentation

- [x] 5.1 In `backend/literature/ingestion/formulation_ingest.py`, wrap the per-submission terminal outcome in `FORMULATION_INGEST_TOTAL.labels(result=...).inc()` for each of `created|updated|rejected|error`
- [x] 5.2 In the recommendation scorer (`backend/core/profiles/recommendations.py` or wherever `RecommendationViewSet.score` lives), time each scoring call with `RECOMMENDATION_SCORE_SECONDS.labels(excluded=..., confidence_band=...).observe(elapsed)`
- [x] 5.3 In `backend/literature/clients/inci_client.py`, `pubchem_client.py`, `pubmed_client.py`, and the OpenAI-facing enrichment client, wrap each outbound request with `EXTERNAL_API_REQUEST_SECONDS.labels(service=..., outcome=...).observe(elapsed)`; classify outcome per the enum in `metrics.py`

## 6. Multiprocess support (backend HTTP)

- [x] 6.1 In `backend/deploy/entrypoint.sh`, when `PROMETHEUS_METRICS_ENABLED=true`, `mkdir -p "$PROMETHEUS_MULTIPROC_DIR"` and `rm -rf "$PROMETHEUS_MULTIPROC_DIR"/*` before exec'ing Gunicorn so stale worker files never leak across restarts
- [x] 6.2 Export `PROMETHEUS_MULTIPROC_DIR` into the environment Gunicorn inherits (entrypoint already exports before exec)
- [x] 6.3 Add a Gunicorn `child_exit` hook (in `backend/deploy/gunicorn.conf.py`, create if absent) that calls `prometheus_client.multiprocess.mark_process_dead(worker.pid)`

## 7. Compose / stack updates

- [x] 7.1 In `docker-compose.yml`, leave `PROMETHEUS_METRICS_ENABLED` unset (defaults to `False`) so local dev is untouched; do not add any port publishing
- [x] 7.2 In `service-compose.yml`, set `PROMETHEUS_METRICS_ENABLED: "true"` on `backend`, `celery`, and `celery-beat`; add `PROMETHEUS_CELERY_WORKER_PORT` / `_BEAT_PORT` env if overriding defaults
- [x] 7.3 In `service-compose.yml`, add `expose: ["9808"]` to `celery` and `expose: ["9809"]` to `celery-beat`; do NOT add `ports:` for either
- [x] 7.4 In `service-compose.yml`, mount a `tmpfs` at the multiprocess dir on `backend`: `tmpfs: - /tmp/prometheus_multiproc:size=64m`
- [x] 7.5 Confirm the Traefik service's dynamic config in the repo (if any) has no router matching `/metrics`; leave a comment in `service-compose.yml` beside the backend service noting `/metrics` is overlay-only

## 8. Tests

- [x] 8.1 Add `backend/core/tests/test_observability.py`. With `PROMETHEUS_METRICS_ENABLED=True` overridden via `@override_settings`, assert `GET /metrics` returns `200`, `Content-Type` starts with `text/plain; version=0.0.4`, and the body contains `django_http_requests_total_by_view_transport_method_total`
- [x] 8.2 In the same test module, with the flag defaulted to `False`, assert `GET /metrics` returns `404`
- [x] 8.3 Add a test that iterates every metric registered on the default registry and asserts each family's observed label values are a subset of the declared `Literal` enum (guards spec §6 cardinality budget)
- [x] 8.4 Add a test that calls `bootstrap.enable_worker_metrics()` with `PROMETHEUS_METRICS_ENABLED=False` and asserts no signals are connected and no port is bound

## 9. Docs

- [x] 9.1 Update `CLAUDE.md` (project) with a short "Observability" section: the three scrape targets, the feature flag, and the local-dev opt-in command
- [x] 9.2 Update `README.md` (or backend README if present) with the same, plus a note that Prometheus itself is provisioned outside this repo
- [x] 9.3 Flagged for a follow-up change once the swarm-deployment spec has been archived onto main; the base commit of this worktree predates it.

## 10. Verification

- [x] 10.1 Run `docker compose run --rm -e PROMETHEUS_METRICS_ENABLED=True backend python manage.py test core.tests.test_observability literature.tests`
- [x] 10.2 Locally: `docker compose up --build` with the flag on, hit `curl -s http://localhost:8000/metrics | head -50` and confirm `django_*` families appear
- [x] 10.3 Locally: `docker compose exec celery curl -s http://localhost:9808/metrics | grep celery_task_total`
- [x] 10.4 Trigger one recommendation score call and confirm `blueskies_recommendation_score_seconds_count` incremented on the next scrape
- [x] 10.5 Trigger one formulation ingest and confirm `blueskies_formulation_ingest_total{result="created"}` incremented
- [ ] 10.6 Operator action post-merge (documented in PR body): deploy to swarm with flag `False`, confirm baseline; flip to `True`, redeploy, verify all three scrape targets return `200` from a shell inside the overlay.
