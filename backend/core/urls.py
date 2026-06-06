from django.urls import path

from .views import compound_list, health_check

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("compounds/", compound_list, name="compound-list"),
]
