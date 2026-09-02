## Why

The Django backend, Celery worker, and Celery beat run in Docker Swarm with no runtime visibility beyond container health probes and ad-hoc log tailing. When request latency spikes, throttles bite, or a nightly literature discovery task stalls, there is no shared, queryable signal to point at — so debugging starts from zero every time. Prometheus scrape endpoints on each backend service unlock the same telemetry the rest of the stack already assumes.

## What Changes

- Add `django-prometheus` to backend requirements and register its app + middleware in `config/settings.py` and `config/urls.py`, gated by a `PROMETHEUS_METRICS_ENABLED` setting so dev/test compose can opt out.
- Expose `GET /metrics` on the backend service, returning Prometheus text-format samples (HTTP request counts/latency histograms, DB query counters via the `django_prometheus` DB backend wrappers, cache counters).
- Instrument the Celery worker: bind Celery signals (`task_prerun`, `task_postrun`, `task_failure`, `task_retry`) to `prometheus_client` counters/histograms and start a `prometheus_client.start_http_server(...)` inside worker startup on a dedicated port (default `9808`), so the same worker replica publishes its own scrape target.
- Instrument Celery beat: publish a lightweight liveness gauge (`celery_beat_last_heartbeat_seconds`) and last-tick timestamp on its own scrape port (default `9809`) via a beat signal hook, so a stuck scheduler is observable without inspecting the shared schedule file.
- Add per-service custom metrics for domain hot paths that already have obvious failure modes: `formulation_ingest_total{result=…}`, `recommendation_score_seconds` histogram (labels: `excluded`, `confidence_band`), `external_api_request_seconds{service=inci|pubchem|pubmed|openai,outcome=…}`.
- Update `service-compose.yml` to expose the three new scrape ports **inside the swarm overlay only** (no published host ports), and document the scrape config Prometheus needs.
- Add settings/env docs for `PROMETHEUS_METRICS_ENABLED`, `PROMETHEUS_CELERY_WORKER_PORT`, `PROMETHEUS_CELERY_BEAT_PORT`, and default the flag to `True` in the prod stack, `False` in local `docker-compose.yml`.

## Capabilities

### New Capabilities
- `backend-observability`: Prometheus scrape endpoints and custom metric families exposed by the Django backend, Celery worker, and Celery beat services, plus the settings/env contract that gates them.

### Modified Capabilities
<!-- None: no existing spec's requirements change. -->

## Impact

- **Code**: `backend/requirements.txt`, `backend/config/settings.py`, `backend/config/urls.py`, new `backend/core/observability/` package (metrics registry, celery signal hooks, worker/beat bootstrap), targeted instrumentation in `literature/ingestion/*`, `literature/clients/*`, and `core/profiles/recommendations.py` (or wherever the recommendation scorer lives).
- **APIs**: New unauthenticated `GET /metrics` on the backend HTTP service; two new scrape sockets on worker/beat containers (overlay-internal).
- **Dependencies**: Add `django-prometheus` (pulls `prometheus-client`, already-installable pure-Python). No new system packages.
- **Deployment**: `service-compose.yml` gains `expose:` entries on the celery services; no new published ports; Traefik config unchanged. Prometheus scrape config (external to this repo) needs three targets: `backend:8000/metrics`, `celery:9808/metrics`, `celery-beat:9809/metrics`.
- **Perf**: `django-prometheus` DB/cache wrappers add per-query counter increments; measured overhead is sub-millisecond and dominated by existing query cost. Metrics endpoint is cheap enough to scrape at 15s.
- **Security**: `/metrics` is unauthenticated by design (standard Prometheus pattern) but MUST remain overlay-internal — Traefik keeps only `web` public, and the new endpoint is on `backend`, which is already private. Explicit note in swarm-deployment spec is out of scope for this change but flagged in tasks.
