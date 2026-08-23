"""Bootstrap functions for enabling Prometheus metrics on worker and beat processes."""
import logging
import os
from pathlib import Path

from django.conf import settings
from prometheus_client import start_http_server, CollectorRegistry, multiprocess

logger = logging.getLogger(__name__)

_worker_started = False
_beat_started = False


def enable_worker_metrics():
    """Enable Prometheus metrics for Celery worker process.

    Short-circuits if PROMETHEUS_METRICS_ENABLED is False.
    Starts an HTTP server on PROMETHEUS_CELERY_WORKER_PORT and connects task signal handlers.
    """
    global _worker_started
    if not getattr(settings, "PROMETHEUS_METRICS_ENABLED", False):
        return
    if _worker_started:
        return
    from . import celery_metrics  # noqa: F401 — registers task_* signal handlers on import

    port = settings.PROMETHEUS_CELERY_WORKER_PORT

    # Enable prometheus_client multiprocess mode for celery worker (prefork pool).
    # The prefork pool forks child processes; without multiprocess mode, child process
    # task signals write to the parent's in-memory registry, which the parent's HTTP
    # server never sees. With multiprocess mode enabled, each process writes to files
    # in PROMETHEUS_MULTIPROC_DIR, and the HTTP server aggregates them on each scrape.
    multiproc_dir = settings.PROMETHEUS_MULTIPROC_DIR
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = multiproc_dir
    Path(multiproc_dir).mkdir(parents=True, exist_ok=True)

    multiproc_registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(multiproc_registry)
    start_http_server(port, registry=multiproc_registry)
    _worker_started = True
    logger.info("Prometheus worker metrics server listening on :%s", port)


def enable_beat_metrics():
    """Enable Prometheus metrics for Celery beat process.

    Short-circuits if PROMETHEUS_METRICS_ENABLED is False.
    Starts an HTTP server on PROMETHEUS_CELERY_BEAT_PORT and registers beat tick handlers.
    """
    global _beat_started
    if not getattr(settings, "PROMETHEUS_METRICS_ENABLED", False):
        return
    if _beat_started:
        return
    from . import celery_metrics

    celery_metrics.register_beat_tick_handler()
    port = settings.PROMETHEUS_CELERY_BEAT_PORT

    # Enable prometheus_client multiprocess mode for consistency with worker.
    # See enable_worker_metrics() for details.
    multiproc_dir = settings.PROMETHEUS_MULTIPROC_DIR
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = multiproc_dir
    Path(multiproc_dir).mkdir(parents=True, exist_ok=True)

    multiproc_registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(multiproc_registry)
    start_http_server(port, registry=multiproc_registry)
    _beat_started = True
    logger.info("Prometheus beat metrics server listening on :%s", port)
