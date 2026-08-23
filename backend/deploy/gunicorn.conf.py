"""Gunicorn config: hooks needed by django-prometheus multiprocess mode."""
import os


def child_exit(server, worker):
    """Mark process as dead for Prometheus multiprocess mode."""
    if os.environ.get("PROMETHEUS_METRICS_ENABLED", "").lower() in {"1", "true", "yes", "on"}:
        from prometheus_client import multiprocess

        multiprocess.mark_process_dead(worker.pid)
