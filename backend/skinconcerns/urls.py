from django.urls import path
from rest_framework.routers import DefaultRouter

from skinconcerns.views import SkinConcernViewSet, SkinProfileConcernView

router = DefaultRouter()
router.register("skin-concerns", SkinConcernViewSet, basename="skin-concern")

urlpatterns = [
    path(
        "skin-profiles/<int:skin_profile_id>/concerns/",
        SkinProfileConcernView.as_view(),
        name="skin-profile-concerns",
    ),
    *router.urls,
]
