"""Tests for the barcode scan feature: ingest_product_by_barcode + ScanBarcodeView."""

from unittest import mock

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from literature.ingestion import inci_client
from literature.ingestion.inci_client import InciProduct
from literature.ingestion.formulation_ingest import ingest_product_by_barcode
from core.models import Formulation, FormulationIngredient
from core.models.brand import Brand
from core.models.product import Product

User = get_user_model()

SCAN_URL = "/api/products/scan-barcode/"

# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

_FAKE_PRODUCT = InciProduct(
    barcode="0123456789012",
    name="Super Serum",
    brand="Blueskies",
    category="Serum",
    country="France",
    image_url="https://example.com/img.jpg",
    ingredients_text="Aqua, Glycerin, Niacinamide",
    inci_list=["Aqua", "Glycerin", "Niacinamide"],
    analysis={"overallSafetyScore": 8, "safetyLevel": "low_risk"},
    raw={"barcode": "0123456789012"},
)


def _mock_get_product(return_value=_FAKE_PRODUCT):
    return mock.patch.object(inci_client, "get_product", return_value=return_value)


def _mock_enrich_delay():
    """Patch the Celery task's .delay so no worker is needed.

    The task is imported lazily inside ingest_product_by_barcode; patching
    core.tasks.enrich_formulation_ingredients replaces the object *on the
    module* so the local `from core.tasks import ...` inside the function
    picks up the mock.
    """
    return mock.patch("core.tasks.enrich_formulation_ingredients", autospec=True)


# ---------------------------------------------------------------------------
# Service-layer tests
# ---------------------------------------------------------------------------

class IngestProductByBarcodeTests(TestCase):
    def test_creates_brand_product_formulation_and_ingredients(self):
        with _mock_get_product(), _mock_enrich_delay():
            result = ingest_product_by_barcode(_FAKE_PRODUCT.barcode)

        self.assertTrue(result.created)
        self.assertEqual(result.barcode, _FAKE_PRODUCT.barcode)
        self.assertEqual(result.ingredient_count, 3)

        # Brand created
        brand = Brand.objects.get(name__iexact="Blueskies")
        self.assertIsNotNone(brand)

        # Product created
        product = Product.objects.get(pk=result.product_id)
        self.assertEqual(product.name, "Super Serum")
        self.assertEqual(product.source, "inciapi")

        # Formulation created
        formulation = Formulation.objects.get(pk=result.formulation_id)
        self.assertEqual(formulation.barcode, _FAKE_PRODUCT.barcode)
        self.assertEqual(formulation.made_in, "France")
        self.assertEqual(formulation.source, "inciapi")
        self.assertIsNotNone(formulation.inci_analysis)
        self.assertEqual(formulation.inci_analysis["safetyLevel"], "low_risk")

        # FormulationIngredient rows
        ingredients = list(
            FormulationIngredient.objects.filter(formulation=formulation).order_by("position")
        )
        self.assertEqual(len(ingredients), 3)
        self.assertEqual(ingredients[0].raw_text, "Aqua")
        self.assertEqual(ingredients[0].position, 1)
        self.assertEqual(ingredients[2].raw_text, "Niacinamide")

    def test_second_call_same_barcode_returns_cached_no_api_call(self):
        # First call — creates everything.
        with _mock_get_product() as mock_api, _mock_enrich_delay():
            first = ingest_product_by_barcode(_FAKE_PRODUCT.barcode)

        self.assertTrue(first.created)
        self.assertEqual(mock_api.call_count, 1)

        # Second call — should NOT call the API.
        with _mock_get_product() as mock_api2, _mock_enrich_delay():
            second = ingest_product_by_barcode(_FAKE_PRODUCT.barcode)

        self.assertFalse(second.created)
        self.assertEqual(second.formulation_id, first.formulation_id)
        mock_api2.assert_not_called()

    def test_get_product_none_raises_value_error(self):
        with _mock_get_product(return_value=None), _mock_enrich_delay():  # pyright: ignore[reportArgumentType]
            with self.assertRaises(ValueError) as ctx:
                ingest_product_by_barcode("9999999999999")
        self.assertIn("9999999999999", str(ctx.exception))

    def test_celery_task_enqueued_after_creation(self):
        with _mock_get_product(), _mock_enrich_delay() as mock_task:
            result = ingest_product_by_barcode(_FAKE_PRODUCT.barcode)

        mock_task.delay.assert_called_once_with(result.formulation_id)

    def test_concurrent_barcode_insert_returns_cached_result(self):
        product = Product.objects.create(name="Super Serum")
        winner = Formulation.objects.create(
            product=product,
            barcode=_FAKE_PRODUCT.barcode,
            raw_inci_text=_FAKE_PRODUCT.ingredients_text,
        )

        with (
            _mock_get_product(),
            _mock_enrich_delay() as mock_task,
            mock.patch(
                "literature.ingestion.formulation_ingest._get_barcode_formulation",
                side_effect=[None, None, winner],
            ),
            mock.patch.object(
                Formulation.objects,
                "create",
                side_effect=IntegrityError("duplicate barcode"),
            ),
        ):
            result = ingest_product_by_barcode(_FAKE_PRODUCT.barcode)

        self.assertFalse(result.created)
        self.assertEqual(result.formulation_id, winner.pk)
        self.assertEqual(result.product_id, winner.product_id)  # pyright: ignore[reportAttributeAccessIssue]
        mock_task.delay.assert_not_called()


# ---------------------------------------------------------------------------
# View-layer tests
# ---------------------------------------------------------------------------

class ScanBarcodeViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(  # pyright: ignore[reportAttributeAccessIssue]
            username="scanner",
            email="scanner@example.com",
            password="testpass123",
        )

    def _auth(self):
        self.client.force_authenticate(user=self.user)  # pyright: ignore[reportAttributeAccessIssue]

    def test_unauthenticated_returns_401_or_403(self):
        response = self.client.post(
            SCAN_URL,
            {"barcode": _FAKE_PRODUCT.barcode},
            format="json",
        )
        self.assertIn(response.status_code, [401, 403])

    def test_missing_barcode_returns_400(self):
        self._auth()
        response = self.client.post(SCAN_URL, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("barcode", response.data.get("detail", ""))  # pyright: ignore[reportAttributeAccessIssue]

    def test_unknown_barcode_returns_404(self):
        self._auth()
        with _mock_get_product(return_value=None), _mock_enrich_delay():  # pyright: ignore[reportArgumentType]
            response = self.client.post(
                SCAN_URL,
                {"barcode": "9999999999999"},
                format="json",
            )
        self.assertEqual(response.status_code, 404)

    def test_new_barcode_returns_201_with_formulation(self):
        self._auth()
        with _mock_get_product(), _mock_enrich_delay():
            response = self.client.post(
                SCAN_URL,
                {"barcode": _FAKE_PRODUCT.barcode},
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        data = response.data  # pyright: ignore[reportAttributeAccessIssue]
        self.assertTrue(data["created"])
        self.assertEqual(data["barcode"], _FAKE_PRODUCT.barcode)
        formulation_data = data["formulation"]
        self.assertEqual(formulation_data["barcode"], _FAKE_PRODUCT.barcode)
        self.assertIn("ingredients", formulation_data)

    def test_existing_barcode_returns_200_not_created(self):
        self._auth()
        # First scan creates the formulation.
        with _mock_get_product(), _mock_enrich_delay():
            r1 = self.client.post(
                SCAN_URL,
                {"barcode": _FAKE_PRODUCT.barcode},
                format="json",
            )
        self.assertEqual(r1.status_code, 201)

        # Second scan hits the cache.
        with _mock_get_product() as mock_api, _mock_enrich_delay():
            r2 = self.client.post(
                SCAN_URL,
                {"barcode": _FAKE_PRODUCT.barcode},
                format="json",
            )
        self.assertEqual(r2.status_code, 200)
        self.assertFalse(r2.data["created"])  # pyright: ignore[reportAttributeAccessIssue]
        mock_api.assert_not_called()
