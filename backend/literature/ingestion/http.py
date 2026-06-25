"""Shared rate-limited HTTP helper for external API clients."""

from __future__ import annotations

import logging
import threading
import time

import requests

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
    )


def _request(kind, url, *, params, headers, limiter, timeout, max_retries, backoff):
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        if limiter is not None:
            limiter.wait()
        try:
            response = requests.get(
                url, params=params, headers=headers, timeout=timeout
            )
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
