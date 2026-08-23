## Purpose

Defines the Prometheus-compatible metrics surface every backend process (Django HTTP server, Celery worker, Celery beat) exposes for scraping, so operators can observe request latency, task throughput, scheduler liveness, and hot-path domain events without reading logs.

## ADDED Requirements

### Requirement: Backend HTTP metrics endpoint

The Django backend service SHALL serve a `GET /metrics` endpoint that returns Prometheus text format (`Content-Type` starts with `text/plain; version=` — the exact `version=` value tracks the `prometheus-client` release), containing at minimum request-count, request-latency-histogram, response-size, and database-query counters for every registered view.

#### Scenario: Metrics endpoint reachable with feature enabled
- **WHEN** `PROMETHEUS_METRICS_ENABLED=True` and a client issues `GET /metrics` against the backend service
- **THEN** the response status is `200`, the `Content-Type` header starts with `text/plain; version=` (any Prometheus text-format version — `0.0.4` and `1.0.0` are both compliant), and the body contains at least the metric families `django_http_requests_total_by_view_transport_method_total`, `django_http_requests_latency_seconds_by_view_method_bucket`, and `django_db_execute_total`

#### Scenario: Metrics endpoint disabled by feature flag
- **WHEN** `PROMETHEUS_METRICS_ENABLED=False` and a client issues `GET /metrics`
- **THEN** the response status is `404`

#### Scenario: Metrics endpoint is unauthenticated
- **WHEN** an unauthenticated client on the swarm overlay issues `GET /metrics` with feature enabled
- **THEN** the response status is `200` and no session cookie, CSRF token, or auth header is required

### Requirement: Backend HTTP request instrumentation

The backend SHALL record one increment on the request counter and one observation on the latency histogram for every HTTP request that reaches Django, labeled by view name, HTTP method, and response status class, including responses produced by DRF viewsets.

#### Scenario: Successful API request produces metric samples
- **WHEN** a client calls `GET /api/health/` and the endpoint returns `200`
- **THEN** a subsequent scrape shows `django_http_responses_total_by_status_view_method_total{status="200",view="core:health-check",method="GET"}` incremented by at least 1 and a matching latency-histogram sample

#### Scenario: Throttled request is still counted
- **WHEN** a client exceeds a DRF throttle scope and receives `429`
- **THEN** the response is counted in `django_http_responses_total_by_status_view_method_total{status="429",...}`

### Requirement: Celery worker metrics endpoint

Every Celery worker replica SHALL expose a Prometheus scrape endpoint on a dedicated TCP port (default `9808`, overridable via `PROMETHEUS_CELERY_WORKER_PORT`) reachable inside the swarm overlay, returning task-level metrics for that worker's process.

#### Scenario: Worker scrape endpoint is up
- **WHEN** the Celery worker container is healthy and a scraper issues `GET :9808/metrics`
- **THEN** the response status is `200` and the body contains the metric families `celery_task_total`, `celery_task_runtime_seconds`, and `celery_task_failure_total`

#### Scenario: Task success recorded
- **WHEN** a Celery task named `core.tasks.daily_literature_discovery_task` completes successfully
- **THEN** the next scrape shows `celery_task_total{task="core.tasks.daily_literature_discovery_task",state="SUCCESS"}` incremented by 1 and one observation added to `celery_task_runtime_seconds{task="core.tasks.daily_literature_discovery_task"}`

#### Scenario: Task failure and retry recorded
- **WHEN** a Celery task raises an exception and Celery emits a retry
- **THEN** `celery_task_failure_total{task=…,exception=…}` and `celery_task_retry_total{task=…}` are incremented on the next scrape

### Requirement: Celery beat liveness metrics endpoint

The Celery beat process SHALL expose a Prometheus scrape endpoint on a dedicated TCP port (default `9809`, overridable via `PROMETHEUS_CELERY_BEAT_PORT`) inside the swarm overlay, publishing at minimum a gauge that reports seconds since the scheduler last woke.

#### Scenario: Beat heartbeat is fresh
- **WHEN** Celery beat has ticked within the last scrape interval and a scraper issues `GET :9809/metrics`
- **THEN** the response contains `celery_beat_last_tick_seconds` with a Unix timestamp within the last 5 minutes and `celery_beat_seconds_since_last_tick` less than the beat's `max_interval` plus one scrape interval

#### Scenario: Beat is stuck
- **WHEN** the Celery beat process is running but the scheduler loop has not advanced for more than `max_interval` seconds
- **THEN** `celery_beat_seconds_since_last_tick` monotonically grows on each scrape, distinguishing "stuck" from "crashed" (which would fail the scrape entirely)

### Requirement: Domain hot-path metrics

The backend SHALL publish counters and histograms for domain operations whose failure modes matter for ops: formulation ingestion outcomes, recommendation scoring latency, and external API calls to INCI, PubChem, PubMed, and OpenAI.

#### Scenario: Formulation ingest outcome recorded
- **WHEN** the ingestion pipeline processes one formulation submission
- **THEN** `blueskies_formulation_ingest_total{result="created"|"updated"|"rejected"|"error"}` is incremented exactly once for that submission, with `result` reflecting the terminal outcome

#### Scenario: Recommendation score latency observed
- **WHEN** the recommendation scorer runs against one formulation for one profile
- **THEN** one observation is added to `blueskies_recommendation_score_seconds_bucket` with labels `excluded={"true"|"false"}` and `confidence_band={"high"|"medium"|"low"}`

#### Scenario: External API call latency and outcome recorded
- **WHEN** an ingestion or enrichment path calls an external service (INCI, PubChem, PubMed, OpenAI)
- **THEN** one observation is added to `blueskies_external_api_request_seconds_bucket{service=…,outcome="success"|"http_error"|"transport_error"|"rate_limited"}` and the corresponding `_count` reflects the call

### Requirement: Metrics endpoint network exposure

Metrics scrape endpoints (backend `/metrics`, worker `:9808`, beat `:9809`) MUST NOT be published to hosts outside the swarm overlay; they SHALL be reachable only to services attached to the internal network.

#### Scenario: Prod stack file does not publish scrape ports
- **WHEN** `service-compose.yml` is inspected
- **THEN** the celery worker and celery beat services declare their scrape ports under `expose:` and NOT under `ports:`, and Traefik has no router pointing at `/metrics`

#### Scenario: Backend metrics reachable only inside the overlay
- **WHEN** an external client resolves the public web host and requests `/metrics` through Traefik
- **THEN** Traefik returns its default 404/routing response and no backend metric family leaks

### Requirement: Metrics feature flag defaults

The metrics surface SHALL be controlled by `PROMETHEUS_METRICS_ENABLED`, defaulting to `True` in the production `service-compose.yml` stack and `False` in local `docker-compose.yml`, so contributor laptops do not incur the instrumentation cost or pay attention to a scrape port nobody scrapes.

#### Scenario: Production stack enables metrics by default
- **WHEN** the stack is deployed from `service-compose.yml` with no override
- **THEN** `PROMETHEUS_METRICS_ENABLED` is `True` on the backend, celery, and celery-beat services

#### Scenario: Local dev disables metrics by default
- **WHEN** a contributor runs `docker compose up --build` with no override
- **THEN** `PROMETHEUS_METRICS_ENABLED` is `False`, `GET /metrics` returns `404`, and no extra port is bound on the celery containers
