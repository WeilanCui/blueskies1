"""Prometheus metrics registry for custom domain metrics."""
import time
from typing import Literal

from prometheus_client import Counter, Gauge, Histogram

FormulationIngestResult = Literal["created", "updated", "rejected", "error"]
ExternalAPIService = Literal["inci", "pubchem", "pubmed", "openai"]
ExternalAPIOutcome = Literal["success", "http_error", "transport_error", "rate_limited"]

FORMULATION_INGEST_TOTAL = Counter(
    "blueskies_formulation_ingest_total",
    "Terminal outcomes of formulation ingestion pipeline",
    labelnames=["result"],
)

RECOMMENDATION_SCORE_SECONDS = Histogram(
    "blueskies_recommendation_score_seconds",
    "Wall-clock time to score one formulation for one profile",
    labelnames=["excluded", "confidence_band"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

EXTERNAL_API_REQUEST_SECONDS = Histogram(
    "blueskies_external_api_request_seconds",
    "Wall-clock time and outcome for outbound external API calls",
    labelnames=["service", "outcome"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)

CELERY_BEAT_LAST_TICK_SECONDS = None  # type: ignore[assignment]
CELERY_BEAT_SECONDS_SINCE_LAST_TICK = None  # type: ignore[assignment]


def _get_or_create_beat_gauges():
    """Lazy initialize beat gauges on first call."""
    global CELERY_BEAT_LAST_TICK_SECONDS, CELERY_BEAT_SECONDS_SINCE_LAST_TICK
    if CELERY_BEAT_LAST_TICK_SECONDS is None:
        CELERY_BEAT_LAST_TICK_SECONDS = Gauge(
            "celery_beat_last_tick_seconds",
            "Unix timestamp of the last time Celery beat's scheduler ticked",
            multiprocess_mode="max",
        )
    if CELERY_BEAT_SECONDS_SINCE_LAST_TICK is None:
        CELERY_BEAT_SECONDS_SINCE_LAST_TICK = Gauge(
            "celery_beat_seconds_since_last_tick",
            "Seconds elapsed since the last Celery beat scheduler tick",
            multiprocess_mode="max",
        )
    return CELERY_BEAT_LAST_TICK_SECONDS, CELERY_BEAT_SECONDS_SINCE_LAST_TICK


def classify_http_outcome(status_code: int | None, exc: BaseException | None) -> ExternalAPIOutcome:
    """Classify an HTTP request outcome to one of the metric label values."""
    if exc is not None:
        # Network/timeout errors are transport errors
        exc_type = type(exc).__name__
        if any(
            name in exc_type
            for name in ["ConnectionError", "Timeout", "ProxyError", "SSLError", "RequestException"]
        ):
            return "transport_error"

    if status_code == 429:
        return "rate_limited"

    if status_code and status_code >= 400:
        return "http_error"

    return "success"
