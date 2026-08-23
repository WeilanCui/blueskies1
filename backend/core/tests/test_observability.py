"""Tests for the backend-observability capability."""
from unittest import mock

from django.test import Client, TestCase, override_settings

from core.observability import bootstrap, metrics as obs_metrics
from core.observability.celery_metrics import (
    CELERY_TASK_TOTAL,
    CELERY_TASK_FAILURE_TOTAL,
    CELERY_TASK_RETRY_TOTAL,
)


class MetricsEndpointEnabledTests(TestCase):
    """8.1 — /metrics returns Prometheus text format when flag is on."""

    @override_settings(
        ROOT_URLCONF="core.tests._urls_metrics_enabled",
        PROMETHEUS_METRICS_ENABLED=True,
        MIDDLEWARE=[
            "django_prometheus.middleware.PrometheusBeforeMiddleware",
            "django.middleware.security.SecurityMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
            "django_prometheus.middleware.PrometheusAfterMiddleware",
        ],
    )
    def test_metrics_endpoint_returns_prometheus_text(self):
        client = Client()
        # Prime the request-count family by hitting the metrics endpoint once
        # (the family is only emitted once at least one request has been
        # instrumented by PrometheusAfterMiddleware).
        client.get("/metrics")
        resp = client.get("/metrics")
        self.assertEqual(resp.status_code, 200)
        # Prometheus text format: any version (0.0.4, 1.0.0 both valid)
        self.assertTrue(
            resp["Content-Type"].startswith("text/plain; version="),
            resp["Content-Type"],
        )
        # django_prometheus emits the request-count family after a request:
        self.assertIn(
            b"django_http_requests_total_by_view_transport_method_total",
            resp.content,
        )

    @override_settings(
        ROOT_URLCONF="core.tests._urls_metrics_enabled",
        PROMETHEUS_METRICS_ENABLED=True,
        MIDDLEWARE=[
            "django_prometheus.middleware.PrometheusBeforeMiddleware",
            "django.middleware.security.SecurityMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
            "django_prometheus.middleware.PrometheusAfterMiddleware",
        ],
    )
    def test_successful_view_request_recorded(self):
        """Successful view requests are recorded in django_http_responses_total_by_status_view_method_total."""
        client = Client()
        # Hit the health check endpoint to generate a successful request
        resp = client.get("/api/health/")
        self.assertEqual(resp.status_code, 200)

        # Scrape metrics and verify the health-check endpoint is recorded
        metrics_resp = client.get("/metrics")
        self.assertEqual(metrics_resp.status_code, 200)
        self.assertIn(b"django_http_responses_total_by_status_view_method_total", metrics_resp.content)
        # Verify that the health-check view is mentioned in the metrics
        self.assertIn(b'view="health-check"', metrics_resp.content)

    @override_settings(
        ROOT_URLCONF="core.tests._urls_metrics_enabled",
        PROMETHEUS_METRICS_ENABLED=True,
        MIDDLEWARE=[
            "django_prometheus.middleware.PrometheusBeforeMiddleware",
            "django.middleware.security.SecurityMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
            "django_prometheus.middleware.PrometheusAfterMiddleware",
        ],
        REST_FRAMEWORK={
            "DEFAULT_THROTTLE_CLASSES": [
                "rest_framework.throttling.AnonRateThrottle",
            ],
            # Allow exactly one anonymous request per day; the second is a 429.
            "DEFAULT_THROTTLE_RATES": {
                "anon": "1/day",
            },
        },
    )
    def test_throttled_request_still_counted(self):
        """Throttled (429) requests are still recorded in metrics."""
        # DRF caches THROTTLE_RATES on the class body at import time, so
        # @override_settings(REST_FRAMEWORK=...) does not propagate. Patch it
        # for the scope of this test instead, and clear the cache so any per-
        # scope history from another test cannot leak in.
        from django.core.cache import cache
        from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle

        cache.clear()
        with mock.patch.dict(
            SimpleRateThrottle.THROTTLE_RATES, {"anon": "1/day"}, clear=False
        ):
            # Also flush any cached .rate/.num_requests/.duration on instances the
            # AnonRateThrottle class already produced in the process.
            AnonRateThrottle.rate = "1/day"
            try:
                client = Client()
                # First anonymous request consumes the day's quota.
                first = client.get("/api/compounds/")
                self.assertEqual(first.status_code, 200, first.content)
                # Second one should 429 with `anon: 1/day`.
                second = client.get("/api/compounds/")
                self.assertEqual(second.status_code, 429, second.content)

                # Scrape metrics and verify the 429 status was recorded.
                metrics_resp = client.get("/metrics")
                self.assertEqual(metrics_resp.status_code, 200)
                self.assertIn(
                    b"django_http_responses_total_by_status_view_method_total",
                    metrics_resp.content,
                )
                self.assertIn(b'status="429"', metrics_resp.content)
            finally:
                del AnonRateThrottle.rate
                cache.clear()


class MetricsEndpointDisabledTests(TestCase):
    """8.2 — /metrics returns 404 when flag is off."""

    @override_settings(ROOT_URLCONF="core.tests._urls_metrics_disabled")
    def test_metrics_endpoint_absent_when_disabled(self):
        client = Client()
        resp = client.get("/metrics")
        self.assertEqual(resp.status_code, 404)


class MetricLabelCardinalityTests(TestCase):
    """8.3 — Custom label values stay within declared Literal enums."""

    def test_formulation_ingest_total_uses_declared_result_values(self):
        allowed = set(obs_metrics.FormulationIngestResult.__args__)
        for sample in obs_metrics.FORMULATION_INGEST_TOTAL.collect():
            for m in sample.samples:
                value = m.labels.get("result")
                if value is not None:
                    self.assertIn(value, allowed, f"unexpected result label: {value}")

    def test_external_api_request_seconds_uses_declared_service_and_outcome(self):
        allowed_service = set(obs_metrics.ExternalAPIService.__args__)
        allowed_outcome = set(obs_metrics.ExternalAPIOutcome.__args__)
        for sample in obs_metrics.EXTERNAL_API_REQUEST_SECONDS.collect():
            for m in sample.samples:
                s = m.labels.get("service")
                o = m.labels.get("outcome")
                if s is not None:
                    self.assertIn(s, allowed_service)
                if o is not None:
                    self.assertIn(o, allowed_outcome)

    def test_recommendation_score_seconds_uses_declared_labels(self):
        allowed_excluded = {"true", "false"}
        allowed_confidence_band = {"high", "medium", "low"}
        for sample in obs_metrics.RECOMMENDATION_SCORE_SECONDS.collect():
            for m in sample.samples:
                excluded = m.labels.get("excluded")
                confidence_band = m.labels.get("confidence_band")
                if excluded is not None:
                    self.assertIn(excluded, allowed_excluded)
                if confidence_band is not None:
                    self.assertIn(confidence_band, allowed_confidence_band)

    def test_celery_task_total_uses_valid_state_label(self):
        allowed_states = {"SUCCESS", "FAILURE"}
        # Ensure a sample exists by incrementing a known label value.
        CELERY_TASK_TOTAL.labels(task="test.task", state="SUCCESS").inc()

        # Collect all state labels observed.
        observed_state_labels = []
        for sample in CELERY_TASK_TOTAL.collect():
            for m in sample.samples:
                state = m.labels.get("state")
                if state is not None:
                    observed_state_labels.append(state)
                    self.assertIn(state, allowed_states)

        # Fail if no samples were observed (vacuous test).
        self.assertGreater(len(observed_state_labels), 0)

    def test_celery_task_failure_total_has_task_and_exception_labels(self):
        # Ensure a sample exists by incrementing a known label value.
        CELERY_TASK_FAILURE_TOTAL.labels(task="test.task", exception="ValueError").inc()

        # Collect all observed samples and verify labels are present.
        observed_samples = []
        for sample in CELERY_TASK_FAILURE_TOTAL.collect():
            for m in sample.samples:
                task = m.labels.get("task")
                exception = m.labels.get("exception")
                # Verify the labels are present and non-empty when samples exist
                if task is not None:
                    self.assertIsInstance(task, str)
                    observed_samples.append(m)
                if exception is not None:
                    self.assertIsInstance(exception, str)

        # Fail if no samples were observed (vacuous test).
        self.assertGreater(len(observed_samples), 0)

    @staticmethod
    def _sample_value(metric, labels):
        """Extract the value of a metric sample by its label set."""
        for sample_family in metric.collect():
            for sample in sample_family.samples:
                if sample.name.endswith("_total") and sample.labels == labels:
                    return sample.value
        return 0.0

    def test_celery_task_success_signal_increments_counter(self):
        """Celery task_success signal dispatch increments counter."""
        from celery.signals import task_success

        class _FakeTask:
            name = "test.observability.fake_task"

        before = self._sample_value(
            CELERY_TASK_TOTAL,
            {"task": _FakeTask.name, "state": "SUCCESS"},
        )
        task_success.send(sender=_FakeTask(), result=None)
        after = self._sample_value(
            CELERY_TASK_TOTAL,
            {"task": _FakeTask.name, "state": "SUCCESS"},
        )
        self.assertEqual(after - before, 1)

    def test_celery_task_retry_signal_increments_counter(self):
        """Celery task_retry signal dispatch increments counter."""
        from celery.signals import task_retry

        class _FakeTask:
            name = "test.observability.fake_retry_task"

        before = self._sample_value(
            CELERY_TASK_RETRY_TOTAL,
            {"task": _FakeTask.name},
        )
        task_retry.send(sender=_FakeTask(), request=None, reason="test", einfo=None)
        after = self._sample_value(
            CELERY_TASK_RETRY_TOTAL,
            {"task": _FakeTask.name},
        )
        self.assertEqual(after - before, 1)


class BootstrapDisabledTests(TestCase):
    """8.4 — enable_worker_metrics() is a no-op when flag is off."""

    @override_settings(PROMETHEUS_METRICS_ENABLED=False)
    def test_enable_worker_metrics_is_noop_when_disabled(self):
        # Reset the module-level "already started" flag so this test is independent
        bootstrap._worker_started = False
        with mock.patch("core.observability.bootstrap.start_http_server") as mock_start:
            bootstrap.enable_worker_metrics()
            mock_start.assert_not_called()
        self.assertFalse(bootstrap._worker_started)

    @override_settings(PROMETHEUS_METRICS_ENABLED=False)
    def test_enable_beat_metrics_is_noop_when_disabled(self):
        bootstrap._beat_started = False
        with mock.patch("core.observability.bootstrap.start_http_server") as mock_start:
            bootstrap.enable_beat_metrics()
            mock_start.assert_not_called()
        self.assertFalse(bootstrap._beat_started)
