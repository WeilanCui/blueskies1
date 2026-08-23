"""URLconf fixture with metrics endpoint enabled for testing."""
from django.contrib import admin
from django.urls import include, path
from django_prometheus import exports as prom_exports

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("api/", include("skinconcerns.urls")),
    path("metrics", prom_exports.ExportToDjangoView, name="prometheus-metrics"),
]
