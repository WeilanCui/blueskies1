from django.urls import path

from .views import (
    compound_list,
    contact_submit,
    formulation_detail,
    formulation_submit,
    health_check,
)

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("contact/", contact_submit, name="contact-submit"),
    path("compounds/", compound_list, name="compound-list"),
    path("formulations/submit/", formulation_submit, name="formulation-submit"),
    path(
        "formulations/<int:formulation_id>/",
        formulation_detail,
        name="formulation-detail",
    ),
]
