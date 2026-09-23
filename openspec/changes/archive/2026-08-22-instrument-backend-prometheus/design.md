## Context

See `proposal.md` for motivation. Backend runs three long-lived processes in Swarm from the same image: `backend` (Django/Gunicorn, HTTP, replicas=1 by migration constraint), `celery` (worker), `celery-beat` (scheduler). Only `web` (Next.js) is publicly reachable; everything else is overlay-internal. Cache is shared Redis via `DJANGO_CACHE_URL`. Health probes and settings must survive `docker exec` (see `env_or_file` note in `settings.py`).

Prometheus itself is external to this repo — this change publishes scrape targets; whoever owns the Prometheus deployment adds the scrape config.

## Goals / Non-Goals

**Goals:**
- One consistent metrics contract across all three backend processes with a single feature flag.
- Zero-cost when disabled (no middleware inserted, no ports bound, no signal receivers registered).
- Multi-process-safe: `gunicorn` with worker count > 1 must produce coherent counters.
- Domain metrics only where they answer a question ops already asks (ingest outcomes, recommendation latency, external API health).

**Non-Goals:**
- Distributed tracing (OpenTelemetry, Jaeger). A future change can layer traces on the same wiring.
- Alerting rules, dashboards, recording rules — those live in the Prometheus/Grafana repo, not this one.
- Frontend metrics (Next.js RUM). The `web` service stays as-is.
- Log-based metrics or log shipping.
- Prometheus server, Alertmanager, or Grafana deployment.

## Decisions

### 1. Use `django-prometheus` for the HTTP surface, `prometheus_client` directly for Celery

**Choice:** Add `django-prometheus>=2.3` for Django HTTP + DB/cache instrumentation. Use the underlying `prometheus_client` library directly for Celery signal handlers and custom domain metrics.

**Why:** `django-prometheus` already produces the industry-standard metric family names (`django_http_requests_*`, `django_db_execute_total`, `django_cache_get_total`) that community dashboards consume. Writing the Django middleware and DB backend wrappers by hand duplicates work with no benefit. For Celery, there is no equally standard shim: `celery-prometheus-exporter` is unmaintained since 2019 and requires a sidecar process; `celery-exporter` (danihodovic) also runs as a sidecar. A dozen lines of `@task_prerun.connect` handlers replace the sidecar with in-process instrumentation, and the metrics live in the same registry as domain metrics — one scrape socket per replica, not one plus a sidecar.

**Alternatives considered:**
- Full custom instrumentation (drop `django-prometheus`): rejected — reinvents standard metric names.
- `celery-exporter` sidecar: rejected — adds an extra container per worker, doubles the ops surface, and pulls events over the broker instead of in-process signals.
- OpenTelemetry with a Prometheus exporter: rejected for scope — brings a much larger dependency footprint and a second config surface (`OTEL_*` env vars) for the same output. Nothing forecloses adding OTel later.

### 2. One shared metrics registry per process, exposed on one socket per process

**Choice:** Django serves `/metrics` on its Gunicorn socket via `django_prometheus.exports.ExportToDjangoView`. Celery worker starts `prometheus_client.start_http_server(port)` inside a `celeryd_init` signal handler. Celery beat starts one on a different port inside `beat_init`.

**Why:** Each process already has an event loop / HTTP server; adding one lightweight scrape socket per process keeps the topology `one target per container`. It matches the shape Prometheus service discovery expects and avoids a sidecar pattern.

**Alternatives considered:**
- Pushgateway: rejected — Pushgateway is for batch jobs, not long-lived processes; guidance explicitly warns against this shape.
- Statsd exporter: rejected — extra hop, extra config, no cardinality benefit here.

### 3. Multi-process gunicorn: use `prometheus_client`'s `multiprocess` mode

**Choice:** Set `PROMETHEUS_MULTIPROC_DIR` (via env, default `/tmp/prometheus_multiproc`), mount it as a `tmpfs` in the backend service, and configure `django-prometheus` to use the multiprocess collector. `entrypoint.sh` clears the directory on start to avoid stale metric files across restarts.

**Why:** Even at `replicas: 1`, Gunicorn spawns `WEB_CONCURRENCY` worker processes. Without multiprocess mode, each Gunicorn worker keeps its own in-memory counters and `/metrics` returns whichever worker answered the scrape — counters oscillate. Multiprocess mode writes per-process files that the collector aggregates at scrape time.

**Trade-off:** Some metric types (Gauges) need an explicit `multiprocess_mode` (`livesum`, `max`, etc.). Domain gauges we introduce (e.g. queue-depth) must set this explicitly; a lint-style test in `core.tests.test_observability` will assert every registered gauge has one.

**Alternatives considered:**
- Force `WEB_CONCURRENCY=1`: rejected — halves request capacity to avoid a metrics quirk.
- Run a metrics-only sidecar per replica: rejected — duplicates process count without solving cardinality.

### 4. Celery signal hooks live in `core/observability/celery_metrics.py`

**Choice:** New package `backend/core/observability/` with modules `metrics.py` (registry + custom metric objects), `celery_metrics.py` (signal receivers), `bootstrap.py` (called from `config/celery.py`). `bootstrap.enable_worker_metrics()` connects `celeryd_init` → `start_http_server` and connects the per-task signals; `bootstrap.enable_beat_metrics()` does the same for beat and installs a beat-tick handler.

**Why:** Keeping the wiring in one package makes the feature-flag gate a single import site and makes the "how do I turn this off" answer obvious. Signal receivers must be connected *before* the worker forks children, which is what `celeryd_init` guarantees.

### 5. Metric name and label conventions

- Custom metrics use the `blueskies_` prefix; `django_` and `celery_` families come from the library defaults.
- Label cardinality budget: no free-form user IDs, no formulation IDs, no INCI strings in labels. External-API `service` label is a fixed enum of `{inci, pubchem, pubmed, openai}`. `outcome` label is a fixed enum of `{success, http_error, transport_error, rate_limited}`.
- Histogram buckets: HTTP latency uses `django-prometheus` defaults; `blueskies_recommendation_score_seconds` uses `[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5]`; `blueskies_external_api_request_seconds` uses `[0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30]` (external calls are slow and time out at 30s).

**Why the cardinality rules:** Prometheus storage grows with `series = product(label cardinalities)`. Even 10k users × 3 label combos would blow the local Prom out; enforcing the enum at instrumentation time prevents accidental cardinality explosions in review.

### 6. Feature flag applies at wiring time, not sample time

**Choice:** When `PROMETHEUS_METRICS_ENABLED=False`, do NOT add `django_prometheus` to `INSTALLED_APPS`, do NOT add its middleware, do NOT connect celery signals, do NOT start scrape sockets. `bootstrap.enable_*_metrics()` short-circuits on the flag.

**Why:** A runtime `if enabled: increment()` check on every request is cheap but non-zero; the wiring-time gate makes disabled truly zero-cost and eliminates the port-binding failure mode when the flag is off.

## Risks / Trade-offs

- **Metrics endpoint DoS surface** → Mitigation: overlay-only exposure (spec requirement); no Traefik route; `web` remains the only public service.
- **Multiprocess metric file dir fills up** → Mitigation: `tmpfs` mount with size cap (`64m`); entrypoint `rm -rf $PROMETHEUS_MULTIPROC_DIR/*` on startup; `django-prometheus` handles per-file cleanup on graceful worker exit.
- **Celery signal handler raises → task marked failed** → Mitigation: every handler wraps its body in `try/except Exception: logger.exception(...)`. A metrics bug MUST NOT cost a task retry.
- **Cardinality creep in domain metrics** → Mitigation: enum-typed label values in `metrics.py` (module-level `Literal` types + a test that iterates `REGISTRY.collect()` and asserts each family's `_labelvalues` come from the allowed set).
- **Worker scrape socket port collision** → Mitigation: ports are settable via env; defaults (`9808`, `9809`) sit inside the unofficial Prometheus exporter range.
- **Celery beat runs only one replica ever; if it dies, no metric is emitted at all** → Mitigation: this is a *feature* (scrape failure = process dead); the `seconds_since_last_tick` gauge distinguishes stuck-alive from crashed, which is the useful signal.

## Migration Plan

1. Ship code + settings gated at `PROMETHEUS_METRICS_ENABLED=False`; land migration-free.
2. Verify locally with the flag flipped: `docker compose run --rm -e PROMETHEUS_METRICS_ENABLED=True backend ...` and `curl :8000/metrics`.
3. Deploy to swarm with flag still `False`, confirm no regression in `backend` health/latency.
4. Flip flag to `True` in `service-compose.yml`, `docker stack deploy`, verify all three scrape targets return `200`.
5. Hand scrape config (three targets, 15s interval) to whoever owns the Prometheus deployment.

**Rollback:** flip `PROMETHEUS_METRICS_ENABLED=False` and redeploy. No schema changes, no data migrations, no external state to reconcile.

## Open Questions

- Exact histogram bucket edges for `blueskies_recommendation_score_seconds` — the proposed buckets are a reasonable starting shape; ops may want to widen the tail once we see real distribution. Safe to tune later without changing the spec.
