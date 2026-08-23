import os

from celery import Celery
from celery.signals import beat_init, celeryd_init

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@celeryd_init.connect
def _init_worker_metrics(**_kwargs):
    """Initialize Prometheus metrics for the worker process."""
    from core.observability import bootstrap

    bootstrap.enable_worker_metrics()


@beat_init.connect
def _init_beat_metrics(**_kwargs):
    """Initialize Prometheus metrics for the beat process."""
    from core.observability import bootstrap

    bootstrap.enable_beat_metrics()
