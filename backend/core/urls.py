from django.urls import path

from .views import compound_list, formulation_detail, formulation_submit, health_check

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("compounds/", compound_list, name="compound-list"),
    path("formulations/submit/", formulation_submit, name="formulation-submit"),
    path(
        "formulations/<int:formulation_id>/",
        formulation_detail,
        name="formulation-detail",
    ),
]
