from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.db import connection
from django.db.models import Count, Prefetch, Q
from django.http import Http404
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from literature.ingestion import ingest_formulation, parse_inci_list
from literature.ingestion.formulation_ingest import ingest_product_by_barcode
from literature.ingestion.http import HttpError
from core.models import (
    Compound,
    ContactSubmission,
    DailyCheckIn,
    Formulation,
    Profile,
    ProfileLocation,
    ReactionEvent,
    Routine,
)
from core.models.product import Product
from core.serializers import (
    CompoundSerializer,
    ContactSubmissionSerializer,
    DailyCheckInSerializer,
    FormulationSerializer,
    FormulationSubmitSerializer,
    IntakeSerializer,
    LoginSerializer,
    ProfileLocationSerializer,
    ReactionEventSerializer,
    RoutineAddProductSerializer,
    RoutineSerializer,
    SignupSerializer,
    TodayCheckInSerializer,
    WeatherSnapshotSerializer,
    auth_user_payload,
    catalog_slug,
    intake_payload,
    serialize_catalog_product,
)
from core.services.weather import get_or_fetch_uv_snapshot
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


class ScanBarcodeView(APIView):
    """POST a barcode to fetch, persist, and return the matching product formulation."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        barcode = str(request.data.get("barcode") or "").strip()
        if not barcode:
            return Response(
                {"detail": "barcode is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = ingest_product_by_barcode(barcode)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except HttpError as exc:
            return Response(
                {"detail": f"INCI API error: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        formulation = get_object_or_404(
            Formulation.objects.select_related("product__brand").prefetch_related(
                "ingredients__compound"
            ),
            pk=result.formulation_id,
        )
        return Response(
            {
                "created": result.created,
                "barcode": result.barcode,
                "formulation": FormulationSerializer(formulation).data,
            },
            status=status.HTTP_201_CREATED if result.created else status.HTTP_200_OK,
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
        .annotate(literature_count=Count("literature_links"))
        .prefetch_related(
            "aliases",
            "identifiers",
            "chemical_class_memberships__chemical_class",
            "property_assertions__property_def",
        )
    )


class FormulationViewSet(viewsets.ModelViewSet):
    queryset = Formulation.objects.select_related("product__brand").prefetch_related(
        "ingredients__compound"
    )
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

    def get_throttles(self):  # pyright: ignore[reportIncompatibleMethodOverride]
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


class ProductCatalogViewSet(ReadOnlyResourceViewSet):
    """Public read-only catalog of products with their primary formulation."""

    lookup_field = "pk"
    lookup_url_kwarg = "pk"

    def get_queryset(self):
        return (
            Product.objects.select_related("brand")
            .prefetch_related(
                Prefetch(
                    "formulations",
                    queryset=Formulation.objects.prefetch_related(
                        "ingredients__compound"
                    ).order_by("market", "version_label", "id"),
                )
            )
            .filter(formulations__isnull=False)
            .distinct()
            .order_by("brand__name", "name")
        )

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        query = self.request.query_params.get("q", "").strip()
        if not query:
            return queryset
        return queryset.filter(
            Q(name__icontains=query)
            | Q(display_name__icontains=query)
            | Q(category__icontains=query)
            | Q(description__icontains=query)
            | Q(brand__name__icontains=query)
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return Response(
            [serialize_catalog_product(product) for product in queryset]
        )

    def retrieve(self, request, *args, **kwargs):
        product = self.get_object()
        return Response(serialize_catalog_product(product))

    def get_object(self):
        lookup = self.kwargs[self.lookup_url_kwarg]  # pyright: ignore[reportArgumentType]
        queryset = self.get_queryset()
        if lookup.isdigit():
            return get_object_or_404(queryset, pk=int(lookup))
        for product in queryset:
            if catalog_slug(product) == lookup:
                return product
        raise Http404


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
    http_method_names = ["get", "post", "put", "head", "options"]

    def get_queryset(self):
        return Profile.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return Response(intake_payload(profile))

    def create(self, request, *args, **kwargs):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        status_code = (
            status.HTTP_200_OK
            if profile.skin_profiles.filter(is_current=True).exists()
            else status.HTTP_201_CREATED
        )
        return self._save_intake(request, status_code=status_code)

    def update(self, request, *args, **kwargs):
        Profile.objects.get_or_create(user=request.user)
        return self._save_intake(request, status_code=status.HTTP_200_OK)

    def _save_intake(self, request, *, status_code):
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        profile = Profile.objects.get(user=request.user)
        return Response(intake_payload(profile), status=status_code)


class ProfileLocationViewSet(viewsets.ModelViewSet):
    """Current user's saved locations and cached UV/weather context."""

    serializer_class = ProfileLocationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return (
            ProfileLocation.objects.filter(profile=profile, is_active=True)
            .select_related("location")
            .order_by("-is_default", "label", "id")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        context["profile"] = profile
        return context

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.is_default = False
        instance.save(update_fields=["is_active", "is_default", "updated_at"])

    @action(detail=True, methods=["post"], url_path="set-default")
    def set_default(self, request, pk=None):
        profile_location = self.get_object()
        ProfileLocation.objects.filter(
            profile=profile_location.profile,
            is_default=True,
        ).exclude(pk=profile_location.pk).update(is_default=False)
        profile_location.is_default = True
        profile_location.is_active = True
        profile_location.save(update_fields=["is_default", "is_active", "updated_at"])
        return Response(self.get_serializer(profile_location).data)

    @action(detail=True, methods=["post"], url_path="refresh-weather")
    def refresh_weather(self, request, pk=None):
        profile_location = self.get_object()
        if not profile_location.share_weather_context:
            return Response(
                {"detail": "Weather context sharing is disabled for this location."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        snapshot = get_or_fetch_uv_snapshot(profile_location.location, force=True)
        return Response(
            {
                "profile_location": self.get_serializer(profile_location).data,
                "weather_snapshot": (
                    WeatherSnapshotSerializer(snapshot).data if snapshot else None
                ),
            }
        )

    @action(detail=False, methods=["get"], url_path="current-context")
    def current_context(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile_location = (
            ProfileLocation.objects.filter(profile=profile, is_active=True)
            .select_related("location")
            .order_by("-is_default", "id")
            .first()
        )
        if profile_location is None:
            return Response({"profile_location": None, "weather_snapshot": None})

        snapshot = None
        if profile_location.share_weather_context:
            snapshot = get_or_fetch_uv_snapshot(profile_location.location)
        return Response(
            {
                "profile_location": self.get_serializer(profile_location).data,
                "weather_snapshot": (
                    WeatherSnapshotSerializer(snapshot).data if snapshot else None
                ),
            }
        )


class RoutineViewSet(viewsets.ModelViewSet):
    """Profile-owned skincare routine templates."""

    serializer_class = RoutineSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        queryset = (
            Routine.objects.filter(profile=profile)
            .prefetch_related(
                "items__product__brand",
                "items__formulation__product__brand",
                "items__formulation__ingredients__compound",
            )
            .order_by("time_of_day", "-is_active", "name", "id")
        )
        active = self.request.query_params.get("active")
        if active == "true":
            queryset = queryset.filter(is_active=True)
        elif active == "false":
            queryset = queryset.filter(is_active=False)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        context["profile"] = profile
        return context

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        routine = self.get_object()
        routine.is_active = False
        routine.save(update_fields=["is_active", "updated_at"])
        return Response(self.get_serializer(routine).data)

    @action(detail=False, methods=["post"], url_path="add-product")
    def add_product(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = RoutineAddProductSerializer(
            data=request.data,
            context={"profile": profile},
        )
        serializer.is_valid(raise_exception=True)
        routine = serializer.save()
        routine_serializer = self.get_serializer(routine)
        return Response(
            {
                "routine": routine_serializer.data,
                "item_id": serializer.item.id,
                "created": serializer.created,
            },
            status=status.HTTP_201_CREATED if serializer.created else status.HTTP_200_OK,
        )


class DailyCheckInViewSet(viewsets.ReadOnlyModelViewSet):
    """Current user's daily skin logs and product usage."""

    serializer_class = DailyCheckInSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return (
            DailyCheckIn.objects.filter(profile=profile)
            .prefetch_related(
                "product_uses__product__brand",
                "product_uses__formulation__product__brand",
                "product_uses__routine_item__product__brand",
                "product_uses__routine_item__formulation__product__brand",
            )
            .order_by("-checkin_date", "-created_at")
        )

    @action(detail=False, methods=["get", "post", "put"], url_path="today")
    def today(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        checkin_date = timezone.localdate()
        if request.method.lower() == "get":
            checkin, _ = DailyCheckIn.objects.get_or_create(
                profile=profile,
                checkin_date=checkin_date,
                defaults={
                    "skin_profile": profile.skin_profiles.filter(is_current=True).first(),
                },
            )
            return Response(self.get_serializer(checkin).data)

        serializer = TodayCheckInSerializer(
            data=request.data,
            context={"profile": profile, "checkin_date": checkin_date},
        )
        serializer.is_valid(raise_exception=True)
        checkin = serializer.save()
        return Response(self.get_serializer(checkin).data)


class ReactionEventViewSet(viewsets.ModelViewSet):
    """Current user's reaction log."""

    serializer_class = ReactionEventSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return (
            ReactionEvent.objects.filter(profile=profile)
            .select_related(
                "daily_checkin",
                "routine",
                "routine_item",
                "product__brand",
                "formulation__product__brand",
            )
            .order_by("-occurred_on", "-created_at")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        context["profile"] = profile
        return context

    def perform_create(self, serializer):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        serializer.save(profile=profile)


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
