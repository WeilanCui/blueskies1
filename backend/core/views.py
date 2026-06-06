from django.db import connection
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.models import Compound
from core.serializers import CompoundSerializer


@api_view(["GET"])
def health_check(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()

    return Response(
        {
            "status": "ok",
            "service": "django",
            "database": "connected",
        }
    )


@api_view(["GET"])
def compound_list(request):
    compounds = (
        Compound.objects.all()
        .select_related("structure")
        .prefetch_related(
            "aliases",
            "identifiers",
            "property_assertions__property_def",
            "literature_links",
        )
    )
    serializer = CompoundSerializer(compounds, many=True)
    return Response(serializer.data)
