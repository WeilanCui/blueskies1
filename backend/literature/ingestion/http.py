"""Shared rate-limited HTTP helper for external API clients."""

from __future__ import annotations

import logging
import threading
import time

import requests

from core.observability.metrics import EXTERNAL_API_REQUEST_SECONDS, classify_http_outcome

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple thread-safe minimum-interval limiter."""

    def __init__(self, min_interval: float) -> None:
        self._min_interval = min_interval
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delta = now - self._last
            if delta < self._min_interval:
                time.sleep(self._min_interval - delta)
            self._last = time.monotonic()


class HttpError(Exception):
    """Raised when an external request ultimately fails."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def request_json(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    limiter: RateLimiter | None = None,
    timeout: float = 20.0,
    max_retries: int = 3,
    backoff: float = 0.5,
    service: str | None = None,
) -> dict:
    """GET a URL and parse JSON, retrying on 429/503 and transient errors."""
    return _request(  # pyright: ignore[reportReturnType]
        "json",
        url,
        params=params,
        headers=headers,
        limiter=limiter,
        timeout=timeout,
        max_retries=max_retries,
        backoff=backoff,
        service=service,
    )


def request_text(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    limiter: RateLimiter | None = None,
    timeout: float = 20.0,
    max_retries: int = 3,
    backoff: float = 0.5,
    service: str | None = None,
) -> str:
    """GET a URL and return raw text (used for PubMed XML)."""
    return _request(
        "text",
        url,
        params=params,
        headers=headers,
        limiter=limiter,
        timeout=timeout,
        max_retries=max_retries,
        backoff=backoff,
        service=service,
    )


def _request(kind, url, *, params, headers, limiter, timeout, max_retries, backoff, service=None):
    start = time.perf_counter()
    status_code_seen: int | None = None
    exc_captured: BaseException | None = None
    last_exc: Exception | None = None
    try:
        for attempt in range(1, max_retries + 1):
            if limiter is not None:
                limiter.wait()
            try:
                response = requests.get(
                    url, params=params, headers=headers, timeout=timeout
                )
                status_code_seen = response.status_code
            except requests.RequestException as exc:  # network errors
                last_exc = exc
                logger.warning("HTTP error (attempt %s) for %s: %s", attempt, url, exc)
                time.sleep(backoff * attempt)
                continue

            if response.status_code in (429, 500, 502, 503, 504):
                last_exc = HttpError(
                    f"{response.status_code} from {url}",
                    status_code=response.status_code,
                )
                logger.warning(
                    "Retryable status %s (attempt %s) for %s",
                    response.status_code,
                    attempt,
                    url,
                )
                time.sleep(backoff * attempt)
                continue

            if response.status_code == 404:
                raise HttpError(f"404 Not Found: {url}", status_code=404)

            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                raise HttpError(
                    f"{response.status_code} from {url}",
                    status_code=response.status_code,
                ) from exc
            return response.json() if kind == "json" else response.text

        status_code = last_exc.status_code if isinstance(last_exc, HttpError) else None
        raise HttpError(
            f"Failed after {max_retries} attempts: {url}",
            status_code=status_code,
        ) from last_exc
    except BaseException as e:
        exc_captured = e
        raise
    finally:
        if service:  # only record when caller identified the service
            # When exc_captured is an HttpError with status_code=None (from exhausted retries),
            # classify based on the underlying requests exception instead, so network failures
            # are classified as "transport_error" rather than "success".
            exc_for_classification = exc_captured
            if isinstance(exc_captured, HttpError) and exc_captured.status_code is None and last_exc is not None:
                exc_for_classification = last_exc

            outcome = classify_http_outcome(status_code_seen, exc_for_classification)
            elapsed = time.perf_counter() - start
            EXTERNAL_API_REQUEST_SECONDS.labels(service=service, outcome=outcome).observe(elapsed)
