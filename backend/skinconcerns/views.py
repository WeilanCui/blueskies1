from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import SkinProfile
from skinconcerns.models import SkinConcern
from skinconcerns.serializers import (
    ProfileConcernSelectionSerializer,
    SkinConcernSerializer,
    SkinProfileConcernSerializer,
)
from skinconcerns.services import (
    ConcernSearchService,
    ConcernSelectionService,
)


class SkinConcernViewSet(viewsets.ReadOnlyModelViewSet):
    """Searchable catalog of canonical skin concerns."""

    serializer_class = SkinConcernSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        return (
            SkinConcern.objects.filter(is_active=True)
            .prefetch_related("aliases", "referral_triggers")
            .order_by("group", "display_name")
        )

    def list(self, request, *args, **kwargs):
        grouped = ConcernSearchService().grouped_common()
        return Response(
            {
                "groups": [
                    {
                        "group": group["group"],
                        "label": group["label"],
                        "concerns": self.get_serializer(
                            group["concerns"],
                            many=True,
                        ).data,
                    }
                    for group in grouped
                ]
            }
        )

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        query = request.query_params.get("q", "")
        limit = self._search_limit(request.query_params.get("limit"))
        results = ConcernSearchService().search(query, limit=limit)
        return Response(
            {
                "query": query,
                "results": self.get_serializer(results, many=True).data,
            }
        )

    def _search_limit(self, value) -> int:
        try:
            return max(1, min(int(value or 12), 50))
        except (TypeError, ValueError):
            return 12


class SkinProfileConcernView(APIView):
    """Read and replace normalized concern selections for a skin profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request, skin_profile_id: int):
        skin_profile = self._skin_profile(request, skin_profile_id)
        return Response(self._payload(skin_profile))

    def post(self, request, skin_profile_id: int):
        skin_profile = self._skin_profile(request, skin_profile_id)
        serializer = ProfileConcernSelectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ConcernSelectionService().set_skin_profile_concerns(
            skin_profile,
            serializer.validated_data["concerns"],
            source=serializer.validated_data["source"],
        )
        return Response(self._payload(skin_profile), status=status.HTTP_200_OK)

    def _skin_profile(self, request, skin_profile_id: int) -> SkinProfile:
        return get_object_or_404(
            SkinProfile,
            pk=skin_profile_id,
            profile__user=request.user,
        )

    def _payload(self, skin_profile: SkinProfile) -> dict:
        selections = list(skin_profile.active_concern_selections())
        return {
            "skin_profile_id": skin_profile.id,
            "concerns": SkinProfileConcernSerializer(selections, many=True).data,
            "policy": skin_profile.concern_policy_for_selections(selections),
        }
