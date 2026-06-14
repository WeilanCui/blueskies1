from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CompoundViewSet,
    ContactSubmissionViewSet,
    DailyCheckInViewSet,
    FormulationViewSet,
    HealthCheckView,
    IntakeViewSet,
    ProductCatalogViewSet,
    ProfileLocationViewSet,
    ReactionEventViewSet,
    RoutineViewSet,
    SessionAuthViewSet,
)

router = DefaultRouter()
router.register("auth", SessionAuthViewSet, basename="auth")
router.register("compounds", CompoundViewSet, basename="compound")
router.register("products", ProductCatalogViewSet, basename="product-catalog")
router.register("formulations", FormulationViewSet, basename="formulation")
router.register("contact", ContactSubmissionViewSet, basename="contact-submission")
router.register("intake", IntakeViewSet, basename="intake")
router.register("profile-locations", ProfileLocationViewSet, basename="profile-location")
router.register("routines", RoutineViewSet, basename="routine")
router.register("daily-checkins", DailyCheckInViewSet, basename="daily-checkin")
router.register("reactions", ReactionEventViewSet, basename="reaction")

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path(
        "intake/",
        IntakeViewSet.as_view({"get": "list", "post": "create", "put": "update"}),
        name="intake",
    ),
    path(
        "contact/",
        ContactSubmissionViewSet.as_view({"post": "create"}),
        name="contact-submit",
    ),
    path(
        "formulations/submit/",
        FormulationViewSet.as_view({"post": "create"}),
        name="formulation-submit",
    ),
    path(
        "formulations/<int:pk>/",
        FormulationViewSet.as_view({"get": "retrieve"}),
        name="formulation-detail",
    ),
    path("", include(router.urls)),
]
