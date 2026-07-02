from django.contrib.auth.models import User
from rest_framework.test import APIClient, APITestCase

from core.models import (
    Brand,
    Compound,
    ConstraintEnforcement,
    ConstraintSeverity,
    Formulation,
    FormulationIngredient,
    Profile,
    ProfileConstraint,
    ProfileConstraintKind,
    Product,
)


class RecommendationScoreAPITests(APITestCase):
    """Test the POST /api/recommendations/score/ endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.profile = Profile.objects.create(user=self.user, handle="testuser")

        # Create a basic formulation with product
        self.brand = Brand.objects.create(name="TestBrand")
        self.product = Product.objects.create(name="TestProduct", brand=self.brand)
        self.formulation = Formulation.objects.create(
            product=self.product,
            raw_inci_text="Water, Glycerin",
        )
        FormulationIngredient.objects.create(
            formulation=self.formulation,
            position=1,
            raw_text="Water",
        )
        FormulationIngredient.objects.create(
            formulation=self.formulation,
            position=2,
            raw_text="Glycerin",
        )

        # Create a compound for constraint testing
        self.retinol = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
        )

    def test_score_base_score_no_constraints(self):
        """Authenticated user scores a formulation with no constraints."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/recommendations/score/",
            {"formulation_id": self.formulation.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["formulation_id"], self.formulation.id)
        self.assertEqual(data["product_name"], "TestProduct")
        self.assertEqual(data["brand_name"], "TestBrand")
        self.assertEqual(data["final_score"], 100)
        self.assertFalse(data["excluded"])
        self.assertEqual(data["reasons"], [])
        self.assertEqual(data["warnings"], [])
        self.assertEqual(data["penalties"], [])
        self.assertEqual(data["boosts"], [])

    def test_score_excluded_formulation(self):
        """Formulation matches a hard exclusion constraint."""
        self.client.force_login(self.user)

        # Create a formulation with the excluded ingredient
        formulation_with_retinol = Formulation.objects.create(
            product=self.product,
            raw_inci_text="Water, Retinol",
        )
        FormulationIngredient.objects.create(
            formulation=formulation_with_retinol,
            position=1,
            raw_text="Water",
        )
        FormulationIngredient.objects.create(
            formulation=formulation_with_retinol,
            position=2,
            raw_text="Retinol",
            compound=self.retinol,
        )

        # Add exclude constraint
        constraint = ProfileConstraint.objects.create(
            profile=self.profile,
            kind=ProfileConstraintKind.ALLERGY,
            enforcement=ConstraintEnforcement.EXCLUDE,
            severity=ConstraintSeverity.CRITICAL,
            compound=self.retinol,
            is_active=True,
        )

        response = self.client.post(
            "/api/recommendations/score/",
            {"formulation_id": formulation_with_retinol.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["excluded"])
        self.assertEqual(data["final_score"], 0)
        self.assertGreater(len(data["reasons"]), 0)
        self.assertTrue(
            any("Excluded" in reason for reason in data["reasons"])
        )

    def test_score_unknown_formulation_404(self):
        """Unknown formulation id returns 404."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/recommendations/score/",
            {"formulation_id": 99999},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_score_missing_formulation_id_400(self):
        """Missing formulation_id in request returns 400."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/recommendations/score/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_score_invalid_formulation_id_400(self):
        """Non-integer formulation_id returns 400."""
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/recommendations/score/",
            {"formulation_id": "not_an_int"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_score_unauthenticated_403(self):
        """Unauthenticated request returns 403."""
        response = self.client.post(
            "/api/recommendations/score/",
            {"formulation_id": self.formulation.id},
            format="json",
        )

        self.assertEqual(response.status_code, 403)


class RecommendationListAPITests(APITestCase):
    """Test the GET /api/recommendations/ endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.profile = Profile.objects.create(user=self.user, handle="testuser")

        self.brand = Brand.objects.create(name="TestBrand")

        # Create multiple formulations
        self.product1 = Product.objects.create(name="Product A", brand=self.brand)
        self.formulation1 = Formulation.objects.create(
            product=self.product1,
            raw_inci_text="Water",
        )
        FormulationIngredient.objects.create(
            formulation=self.formulation1,
            position=1,
            raw_text="Water",
        )

        self.product2 = Product.objects.create(name="Product B", brand=self.brand)
        self.formulation2 = Formulation.objects.create(
            product=self.product2,
            raw_inci_text="Water, Glycerin",
        )
        FormulationIngredient.objects.create(
            formulation=self.formulation2,
            position=1,
            raw_text="Water",
        )

        # Create a compound for exclusion
        self.retinol = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
        )
        self.product3 = Product.objects.create(name="Product C", brand=self.brand)
        self.formulation3 = Formulation.objects.create(
            product=self.product3,
            raw_inci_text="Water, Retinol",
        )
        FormulationIngredient.objects.create(
            formulation=self.formulation3,
            position=1,
            raw_text="Water",
        )
        FormulationIngredient.objects.create(
            formulation=self.formulation3,
            position=2,
            raw_text="Retinol",
            compound=self.retinol,
        )

    def test_list_descending_score_order(self):
        """Results are ordered by descending final_score."""
        self.client.force_login(self.user)
        response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data["results"]

        # All formulations should be returned in order
        self.assertEqual(len(results), 3)

        # Verify descending score order
        for i in range(len(results) - 1):
            self.assertGreaterEqual(
                results[i]["final_score"],
                results[i + 1]["final_score"],
            )

    def test_list_excluded_hidden_by_default(self):
        """Hard-excluded formulations are hidden by default."""
        self.client.force_login(self.user)

        # Create exclude constraint
        ProfileConstraint.objects.create(
            profile=self.profile,
            kind=ProfileConstraintKind.ALLERGY,
            enforcement=ConstraintEnforcement.EXCLUDE,
            severity=ConstraintSeverity.CRITICAL,
            compound=self.retinol,
            is_active=True,
        )

        response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data["results"]

        # Only 2 formulations should be returned (excluded one hidden)
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertFalse(result["excluded"])

    def test_list_include_excluded_true(self):
        """include_excluded=true includes excluded formulations."""
        self.client.force_login(self.user)

        # Create exclude constraint
        ProfileConstraint.objects.create(
            profile=self.profile,
            kind=ProfileConstraintKind.ALLERGY,
            enforcement=ConstraintEnforcement.EXCLUDE,
            severity=ConstraintSeverity.CRITICAL,
            compound=self.retinol,
            is_active=True,
        )

        response = self.client.get("/api/recommendations/?include_excluded=true")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data["results"]

        # All 3 formulations should be returned
        self.assertEqual(len(results), 3)

        # Excluded ones should be at the end
        excluded_items = [r for r in results if r["excluded"]]
        self.assertEqual(len(excluded_items), 1)
        self.assertEqual(excluded_items[0]["final_score"], 0)

    def test_list_pagination(self):
        """Results are paginated at 20 per page."""
        self.client.force_login(self.user)

        # Create enough formulations to exceed one page
        for i in range(25):
            product = Product.objects.create(
                name=f"Product {i}",
                brand=self.brand,
            )
            formulation = Formulation.objects.create(
                product=product,
                raw_inci_text="Water",
            )
            FormulationIngredient.objects.create(
                formulation=formulation,
                position=1,
                raw_text="Water",
            )

        response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # First page should have 20 items
        self.assertEqual(len(data["results"]), 20)
        self.assertIsNotNone(data["next"])
        self.assertIsNone(data["previous"])

        # Second page should have remaining items
        response2 = self.client.get(data["next"])
        self.assertEqual(response2.status_code, 200)
        data2 = response2.json()
        # 25 created + 3 from setUp = 28 total, so second page has 8
        self.assertEqual(len(data2["results"]), 8)

    def test_list_empty_catalog(self):
        """Empty catalog returns empty paginated result."""
        self.client.force_login(self.user)

        # Create a new user with no products
        other_user = User.objects.create_user(username="otheruser")
        other_profile = Profile.objects.create(user=other_user, handle="otheruser")

        # Delete all products
        Product.objects.all().delete()

        self.client.force_login(other_user)
        response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["results"]), 0)
        self.assertIsNone(data["next"])
        self.assertIsNone(data["previous"])

    def test_list_unauthenticated_403(self):
        """Unauthenticated request returns 403."""
        response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, 403)

    def test_list_include_excluded_1_param(self):
        """include_excluded=1 is treated as true."""
        self.client.force_login(self.user)

        # Create exclude constraint
        ProfileConstraint.objects.create(
            profile=self.profile,
            kind=ProfileConstraintKind.ALLERGY,
            enforcement=ConstraintEnforcement.EXCLUDE,
            severity=ConstraintSeverity.CRITICAL,
            compound=self.retinol,
            is_active=True,
        )

        response = self.client.get("/api/recommendations/?include_excluded=1")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data["results"]

        # All 3 formulations should be returned
        self.assertEqual(len(results), 3)
