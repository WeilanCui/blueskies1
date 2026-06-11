from django.urls import path

from .views import (
    auth_login,
    auth_logout,
    auth_me,
    auth_signup,
    compound_list,
    contact_submit,
    formulation_detail,
    formulation_submit,
    health_check,
    intake,
)

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("auth/me/", auth_me, name="auth-me"),
    path("auth/signup/", auth_signup, name="auth-signup"),
    path("auth/login/", auth_login, name="auth-login"),
    path("auth/logout/", auth_logout, name="auth-logout"),
    path("intake/", intake, name="intake"),
    path("contact/", contact_submit, name="contact-submit"),
    path("compounds/", compound_list, name="compound-list"),
    path("formulations/submit/", formulation_submit, name="formulation-submit"),
    path(
        "formulations/<int:formulation_id>/",
        formulation_detail,
        name="formulation-detail",
    ),
]
