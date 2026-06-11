from django.db import connection
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.ingestion import ingest_formulation, parse_inci_list
from core.models import Compound, Formulation
from core.serializers import (
    CompoundSerializer,
    ContactSubmissionSerializer,
    FormulationSerializer,
    FormulationSubmitSerializer,
)


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
            "chemical_class_memberships__chemical_class",
            "property_assertions__property_def",
            "literature_links",
        )
    )
    serializer = CompoundSerializer(compounds, many=True)
    return Response(serializer.data)


@api_view(["POST"])
def formulation_submit(request):
    serializer = FormulationSubmitSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = serializer.validated_data
    ingredient_names = parse_inci_list(data["formulation"])
    if not ingredient_names:
        return Response(
            {"detail": "No ingredients found in the formulation text."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    result = ingest_formulation(
        data["name"],
        data["formulation"],
        brand=data.get("brand", ""),
    )

    formulation = get_object_or_404(Formulation, pk=result.formulation_id)
    return Response(
        {
            "formulation": FormulationSerializer(formulation).data,
            "ingestion": {
                "ingredient_count": result.ingredient_count,
                "enrichment_status": result.enrichment_status,
                "ingredients": [
                    {
                        "name": item.name,
                        "position": item.position,
                        "compound_id": item.compound_id,
                        "parse_status": item.parse_status,
                        "inci_properties": item.inci_properties,
                        "pubchem_descriptors": item.pubchem_descriptors,
                        "articles_linked": item.articles_linked,
                        "errors": item.errors,
                    }
                    for item in result.ingredients
                ],
            },
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def formulation_detail(request, formulation_id: int):
    formulation = get_object_or_404(
        Formulation.objects.prefetch_related("ingredients__compound"),
        pk=formulation_id,
    )
    return Response(FormulationSerializer(formulation).data)


@api_view(["POST"])
def contact_submit(request):
    serializer = ContactSubmissionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    contact = serializer.save(
        user=request.user if request.user.is_authenticated else None,
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:2048],
    )
    return Response(
        {
            "id": contact.id,
            "detail": "Thanks for reaching out. We will reach out shortly.",
        },
        status=status.HTTP_201_CREATED,
    )
