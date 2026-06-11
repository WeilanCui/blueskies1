from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.db import connection
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from literature.ingestion import ingest_formulation, parse_inci_list
from core.models import Compound, ContactSubmission, Formulation, Profile
from core.serializers import (
    CompoundSerializer,
    ContactSubmissionSerializer,
    FormulationSerializer,
    FormulationSubmitSerializer,
    IntakeSerializer,
    LoginSerializer,
    SignupSerializer,
    auth_user_payload,
    intake_payload,
)
from core.throttles import (
    AuthRateThrottle,
    ContactRateThrottle,
    FormulationSubmitRateThrottle,
    SignupRateThrottle,
)


class HealthCheckView(APIView):
    """Small operational endpoint kept outside model resources."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
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


class ReadOnlyResourceViewSet(viewsets.ReadOnlyModelViewSet):
    """Shared base for public read-only catalog resources."""

    permission_classes = [AllowAny]


class CreateOnlyModelViewSet(viewsets.ModelViewSet):
    """Shared base for model-backed endpoints that only expose creation."""

    http_method_names = ["post", "head", "options"]


class CompoundViewSet(ReadOnlyResourceViewSet):
    serializer_class = CompoundSerializer
    queryset = (
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


class FormulationViewSet(viewsets.ModelViewSet):
    queryset = Formulation.objects.prefetch_related("ingredients__compound")
    serializer_class = FormulationSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return FormulationSubmitSerializer
        return FormulationSerializer

    def get_permissions(self):
        permission_classes = (
            [IsAuthenticated] if self.action == "create" else [AllowAny]
        )
        return [permission() for permission in permission_classes]

    def get_throttles(self):
        throttle_classes = (
            [FormulationSubmitRateThrottle] if self.action == "create" else []
        )
        return [throttle() for throttle in throttle_classes]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
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


class SessionAuthViewSet(viewsets.ViewSet):
    """Session-backed auth endpoints grouped under /api/auth/."""

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    @action(detail=False, methods=["get"], url_path="me", url_name="me")
    def me(self, request):
        get_token(request)
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response({"user": auth_user_payload(request.user)})

    @action(
        detail=False,
        methods=["post"],
        url_path="signup",
        url_name="signup",
        throttle_classes=[SignupRateThrottle],
    )
    def signup(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        django_login(request, user)
        get_token(request)
        return Response(
            {"user": auth_user_payload(user)},
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="login",
        url_name="login",
        throttle_classes=[AuthRateThrottle],
    )
    def login(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        django_login(request, user)
        get_token(request)
        return Response({"user": auth_user_payload(user)})

    @action(detail=False, methods=["post"], url_path="logout", url_name="logout")
    def logout(self, request):
        django_logout(request)
        return Response({"detail": "Logged out."})


class IntakeViewSet(viewsets.ModelViewSet):
    """Current user's intake endpoint backed by the Profile aggregate."""

    serializer_class = IntakeSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return Profile.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return Response(intake_payload(profile))

    def create(self, request, *args, **kwargs):
        Profile.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        profile = Profile.objects.get(user=request.user)
        return Response(intake_payload(profile), status=status.HTTP_201_CREATED)


class ContactSubmissionViewSet(CreateOnlyModelViewSet):
    """Public contact endpoint with creation only; admin handles review."""

    queryset = ContactSubmission.objects.none()
    serializer_class = ContactSubmissionSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ContactRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
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
