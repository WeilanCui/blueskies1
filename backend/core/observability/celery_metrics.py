"""Celery signal handlers for task and beat instrumentation."""
import logging
import threading
import time
from collections import defaultdict

from celery.signals import beat_init, task_failure, task_postrun, task_prerun, task_retry, task_success, worker_process_init
from prometheus_client import Counter, Histogram

from . import metrics

logger = logging.getLogger(__name__)

# Task metrics
CELERY_TASK_TOTAL = Counter(
    "celery_task_total",
    "Celery tasks by terminal state",
    labelnames=["task", "state"],
)

CELERY_TASK_RUNTIME_SECONDS = Histogram(
    "celery_task_runtime_seconds",
    "Task runtime seconds",
    labelnames=["task"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 5, 10, 30, 60, 300, 600, 1800),
)

CELERY_TASK_FAILURE_TOTAL = Counter(
    "celery_task_failure_total",
    "Celery task failures",
    labelnames=["task", "exception"],
)

CELERY_TASK_RETRY_TOTAL = Counter(
    "celery_task_retry_total",
    "Celery task retries",
    labelnames=["task"],
)

# Track task start times per task_id
_task_start_times = {}

# Evict stale task start times older than 24 hours (matches Celery's default task_time_limit)
_MAX_TASK_START_AGE_SECONDS = 86400  # 24h


def _evict_stale_task_starts(now: float) -> None:
    """Remove task start time entries older than the max age threshold.

    Tasks that are killed or hit hard time limits may never reach postrun,
    leaving their start times in the dict forever. This eviction prevents
    unbounded growth.
    """
    stale = [k for k, ts in _task_start_times.items() if now - ts > _MAX_TASK_START_AGE_SECONDS]
    for k in stale:
        _task_start_times.pop(k, None)


@task_prerun.connect
def _on_task_prerun(task_id, task, args, kwargs, **_kw):
    """Record task start time."""
    try:
        now = time.time()
        _task_start_times[task_id] = now
        # Opportunistically evict stale entries when dict is getting large,
        # but not on every task to avoid O(n) work.
        if len(_task_start_times) > 1024:
            _evict_stale_task_starts(now)
    except Exception:
        logger.exception("Error in task_prerun metrics handler")


@task_postrun.connect
def _on_task_postrun(task_id, task, args, kwargs, retval, state, **_kw):
    """Record task runtime."""
    try:
        if task_id in _task_start_times:
            start_time = _task_start_times.pop(task_id)
            elapsed = time.time() - start_time
            CELERY_TASK_RUNTIME_SECONDS.labels(task=task.name).observe(elapsed)
    except Exception:
        logger.exception("Error in task_postrun metrics handler")


@task_success.connect
def _on_task_success(sender, task_id, result, **_kw):
    """Increment task success counter."""
    try:
        CELERY_TASK_TOTAL.labels(task=sender.name, state="SUCCESS").inc()
    except Exception:
        logger.exception("Error in task_success metrics handler")


@task_failure.connect
def _on_task_failure(sender, task_id, exception, einfo, **_kw):
    """Increment task failure counter."""
    try:
        exc_name = type(exception).__name__
        CELERY_TASK_TOTAL.labels(task=sender.name, state="FAILURE").inc()
        CELERY_TASK_FAILURE_TOTAL.labels(task=sender.name, exception=exc_name).inc()
    except Exception:
        logger.exception("Error in task_failure metrics handler")


@task_retry.connect
def _on_task_retry(sender, task_id, reason, einfo, **_kw):
    """Increment task retry counter."""
    try:
        CELERY_TASK_RETRY_TOTAL.labels(task=sender.name).inc()
    except Exception:
        logger.exception("Error in task_retry metrics handler")


@worker_process_init.connect
def _on_worker_process_init(sender, **_kw):
    """Ensure metrics modules are imported in child processes.

    With prometheus_client multiprocess mode enabled, each process writes metrics
    to files in PROMETHEUS_MULTIPROC_DIR. This handler ensures the child process
    imports the metrics modules at initialization, so their Counter/Histogram objects
    are created and configured to write to the multiprocess directory.
    """
    try:
        # Re-import the metrics modules to trigger their module-level Counter/Histogram
        # initialization in this child process, ensuring they write to the multiprocess dir.
        from . import metrics as _  # noqa: F401
        logger.debug("Worker process metrics initialized")
    except Exception:
        logger.exception("Error in worker_process_init metrics handler")


# Beat tick tracking
_last_tick_ts = 0.0
_beat_tick_lock = threading.Lock()


def _update_beat_seconds_since_last_tick():
    """Background thread that updates the seconds_since_last_tick gauge every 5s."""
    global _last_tick_ts
    try:
        while True:
            time.sleep(5)
            with _beat_tick_lock:
                if _last_tick_ts > 0:
                    last_tick, seconds_since = metrics._get_or_create_beat_gauges()
                    elapsed = time.time() - _last_tick_ts
                    seconds_since.set(elapsed)
    except Exception:
        logger.exception("Error updating beat seconds_since_last_tick")


def register_beat_tick_handler():
    """Register beat tick handlers to update beat metrics."""
    global _last_tick_ts

    # Initialize gauges
    last_tick_gauge, _ = metrics._get_or_create_beat_gauges()

    # Start background thread to update the elapsed gauge
    daemon_thread = threading.Thread(target=_update_beat_seconds_since_last_tick, daemon=True)
    daemon_thread.start()

    # Connect beat_init signal
    @beat_init.connect
    def _on_beat_init(sender, **_kw):
        try:
            global _last_tick_ts
            with _beat_tick_lock:
                _last_tick_ts = time.time()
                last_tick_gauge.set(_last_tick_ts)
            logger.info("Prometheus beat metrics initialized")
        except Exception:
            logger.exception("Error in beat_init metrics handler")

    # Monkey-patch the Scheduler.tick method to update metrics
    try:
        from celery.beat import Scheduler

        original_tick = Scheduler.tick

        def _tick_with_metrics(self):
            try:
                result = original_tick(self)
                global _last_tick_ts
                with _beat_tick_lock:
                    _last_tick_ts = time.time()
                    last_tick_gauge.set(_last_tick_ts)
                return result
            except Exception:
                logger.exception("Error in Scheduler.tick metrics wrapper")
                raise

        Scheduler.tick = _tick_with_metrics
    except Exception:
        logger.exception("Error registering Scheduler.tick wrapper")
