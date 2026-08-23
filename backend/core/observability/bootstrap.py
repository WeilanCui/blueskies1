"""Bootstrap functions for enabling Prometheus metrics on worker and beat processes."""
import logging

from django.conf import settings
from prometheus_client import start_http_server

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
    start_http_server(port)
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
    start_http_server(port)
    _beat_started = True
    logger.info("Prometheus beat metrics server listening on :%s", port)
