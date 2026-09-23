from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("api/", include("skinconcerns.urls")),
]

if settings.PROMETHEUS_METRICS_ENABLED:
    from django_prometheus import exports as prom_exports

    urlpatterns.append(path("metrics", prom_exports.ExportToDjangoView, name="prometheus-metrics"))
