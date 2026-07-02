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
    SkinProfile,
)
from skinconcerns.models import (
    ConcernRule,
    RuleKind,
    RuleTargetType,
    SkinConcern,
    SkinProfileConcern,
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
        ProfileConstraint.objects.create(
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
        # Verify excluded item appears at the end
        self.assertTrue(results[-1]["excluded"])

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
        Profile.objects.create(user=other_user, handle="otheruser")

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


class RecommendationConcernRuleAPITests(APITestCase):
    """Test concern rule impacts in recommendation API."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="concernuser", password="testpass")
        self.profile = Profile.objects.create(user=self.user, handle="concernuser")
        self.skin_profile = SkinProfile.objects.create(
            profile=self.profile, is_current=True
        )

        # Create a basic formulation
        self.brand = Brand.objects.create(name="TestBrand")
        self.product = Product.objects.create(name="TestProduct", brand=self.brand)
        self.formulation = Formulation.objects.create(
            product=self.product,
            raw_inci_text="Water, Retinol",
        )
        FormulationIngredient.objects.create(
            formulation=self.formulation,
            position=1,
            raw_text="Water",
        )

        # Create a compound for concern rule testing
        self.retinol = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
        )
        FormulationIngredient.objects.create(
            formulation=self.formulation,
            position=2,
            raw_text="Retinol",
            compound=self.retinol,
        )

        # Create a concern and rule
        self.concern = SkinConcern.objects.create(
            slug="sensitivity",
            display_name="Sensitivity",
            consumer_label="Sensitive skin",
        )
        self.rule = ConcernRule.objects.create(
            concern=self.concern,
            key="avoid-retinol",
            label="Avoid Retinol",
            rule_kind=RuleKind.PENALIZE,
            target_type=RuleTargetType.COMPOUND,
            compound=self.retinol,
            weight=10,
            rationale="Retinol can irritate sensitive skin.",
        )

    def test_concern_rule_impact_includes_source_and_concern_slug(self):
        """Score response includes concern-sourced impacts with source and concern."""
        # Link user to concern
        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.concern,
            confidence=1.0,
        )

        self.client.force_login(self.user)
        response = self.client.post(
            "/api/recommendations/score/",
            {"formulation_id": self.formulation.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check penalties include concern-sourced impact
        self.assertGreater(len(data["penalties"]), 0)
        concern_impacts = [
            impact for impact in data["penalties"] if impact.get("source") == "concern"
        ]

        self.assertTrue(concern_impacts, "expected a concern-sourced penalty")
        concern_impact = concern_impacts[0]
        self.assertEqual(concern_impact["source"], "concern")
        self.assertEqual(concern_impact["concern"], "sensitivity")
        self.assertIn("sensitive skin", concern_impact["reason"].lower())

    def test_constraint_impact_source_is_constraint(self):
        """Constraint impacts have source: constraint."""
        # Create a constraint in addition to concern rule
        ProfileConstraint.objects.create(
            profile=self.profile,
            kind=ProfileConstraintKind.ALLERGY,
            enforcement=ConstraintEnforcement.PENALIZE,
            severity=ConstraintSeverity.MODERATE,
            compound=self.retinol,
            is_active=True,
        )

        # Link user to concern
        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.concern,
            confidence=1.0,
        )

        self.client.force_login(self.user)
        response = self.client.post(
            "/api/recommendations/score/",
            {"formulation_id": self.formulation.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should have both constraint and concern impacts
        penalties = data["penalties"]
        self.assertGreaterEqual(len(penalties), 2)

        sources = [impact["source"] for impact in penalties]
        self.assertIn("constraint", sources)
        self.assertIn("concern", sources)

    def test_no_concern_selected_behaves_like_constraint_only(self):
        """Profile with no concerns scores identically to constraint-only scoring."""
        # Don't link any concerns
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/recommendations/score/",
            {"formulation_id": self.formulation.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # With no concerns and no constraints, score should be base (100)
        self.assertEqual(data["final_score"], 100)
        self.assertEqual(len(data["penalties"]), 0)

    def test_inactive_concern_link_ignored(self):
        """Inactive SkinProfileConcern does not produce impacts."""
        # Create inactive link
        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.concern,
            confidence=1.0,
            is_active=False,
        )

        self.client.force_login(self.user)
        response = self.client.post(
            "/api/recommendations/score/",
            {"formulation_id": self.formulation.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # No concern impacts should be present
        for impact in data["penalties"]:
            self.assertEqual(impact["source"], "constraint")

    def test_list_endpoint_includes_concern_impacts(self):
        """GET /api/recommendations/ includes concern-sourced impacts."""
        # Add a RECOMMEND rule so the rank endpoint carries coverage too
        ConcernRule.objects.create(
            concern=self.concern,
            key="recommend-retinol-alt",
            label="Retinol",
            rule_kind=RuleKind.RECOMMEND,
            target_type=RuleTargetType.COMPOUND,
            compound=self.retinol,
            weight=10,
        )
        # Link user to concern
        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.concern,
            confidence=1.0,
        )

        self.client.force_login(self.user)
        response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data["results"]

        # Every ranked result carries a coverage array
        for result in results:
            self.assertIn("coverage", result)
            self.assertIsInstance(result["coverage"], list)

        # Find our test formulation
        matches = [
            result
            for result in results
            if result["formulation_id"] == self.formulation.id
        ]

        self.assertTrue(matches, "expected the test formulation in the results")
        test_result = matches[0]
        # Should have penalties from concern rule
        self.assertGreater(len(test_result["penalties"]), 0)

        # Check that at least one penalty has source="concern"
        concern_penalties = [p for p in test_result["penalties"] if p.get("source") == "concern"]
        self.assertGreater(len(concern_penalties), 0)

        # Rank endpoint carries the coverage shape for the RECOMMEND match
        self.assertEqual(len(test_result["coverage"]), 1)
        cov = test_result["coverage"][0]
        self.assertEqual(cov["concern"], "sensitivity")
        self.assertEqual(cov["matched"], 1)
        self.assertEqual(cov["total"], 1)
        self.assertIn("Retinol", cov["matched_rules"])

    def test_avoid_rule_warns_never_excludes(self):
        """AVOID rule produces warnings but never excludes formulation."""
        # Deactivate the setUp PENALIZE rule so only the AVOID rule fires
        self.rule.is_active = False
        self.rule.save()
        # Create AVOID rule instead of PENALIZE
        ConcernRule.objects.create(
            concern=self.concern,
            key="avoid-retinol-sensitivity",
            label="Avoid Retinol (Sensitivity)",
            rule_kind=RuleKind.AVOID,
            target_type=RuleTargetType.COMPOUND,
            compound=self.retinol,
            weight=10,
            rationale="Retinol can irritate sensitive skin.",
        )

        # Link user to concern
        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.concern,
            confidence=1.0,
        )

        self.client.force_login(self.user)
        response = self.client.post(
            "/api/recommendations/score/",
            {"formulation_id": self.formulation.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # AVOID produces warnings, not penalties or exclusion
        self.assertGreater(len(data["warnings"]), 0)
        self.assertFalse(data["excluded"])
        self.assertEqual(len(data["penalties"]), 0)

    def test_coverage_array_in_score_response(self):
        """Score response includes coverage array with correct shape."""
        glycerin = Compound.objects.create(
            canonical_inci="GLYCERIN",
            display_name="Glycerin",
        )

        # Create formulation with glycerin
        formulation = Formulation.objects.create(
            product=self.product,
            raw_inci_text="Water, Glycerin",
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=1,
            raw_text="Water",
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=2,
            raw_text="Glycerin",
            compound=glycerin,
        )

        # Create RECOMMEND rule
        ConcernRule.objects.create(
            concern=self.concern,
            key="recommend-glycerin",
            label="Glycerin",
            rule_kind=RuleKind.RECOMMEND,
            target_type=RuleTargetType.COMPOUND,
            compound=glycerin,
            weight=10,
        )

        # Link user to concern
        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.concern,
            confidence=1.0,
        )

        self.client.force_login(self.user)
        response = self.client.post(
            "/api/recommendations/score/",
            {"formulation_id": formulation.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check coverage array exists
        self.assertIn("coverage", data)
        self.assertIsInstance(data["coverage"], list)

        # Verify coverage shape
        self.assertEqual(len(data["coverage"]), 1)
        cov = data["coverage"][0]
        self.assertEqual(cov["concern"], "sensitivity")
        self.assertEqual(cov["concern_label"], "Sensitive skin")
        self.assertEqual(cov["matched"], 1)
        self.assertEqual(cov["total"], 1)
        self.assertIn("Glycerin", cov["matched_rules"])

    def test_coverage_empty_when_no_recommend_rules(self):
        """Coverage array is empty when no RECOMMEND rules active."""
        # Link the concern so the evaluator actually runs; coverage must be
        # empty because the linked concern's only rule is PENALIZE.
        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.concern,
            confidence=1.0,
        )
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/recommendations/score/",
            {"formulation_id": self.formulation.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Coverage should be empty (rule is PENALIZE, not RECOMMEND)
        self.assertEqual(data["coverage"], [])


class RecommendationConfidenceAPITests(APITestCase):
    """Test data confidence in recommendation API."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.profile = Profile.objects.create(user=self.user, handle="testuser")
        self.brand = Brand.objects.create(name="TestBrand")

    def test_score_endpoint_includes_confidence_fields(self):
        """Score endpoint response includes data_confidence and confidence_band."""
        self.client.force_login(self.user)

        product = Product.objects.create(name="TestProduct", brand=self.brand)
        formulation = Formulation.objects.create(product=product, enrichment_status="complete")
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=1,
            raw_text="Water",
        )

        response = self.client.post(
            "/api/recommendations/score/",
            {"formulation_id": formulation.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("data_confidence", data)
        self.assertIn("confidence_band", data)
        self.assertIsInstance(data["data_confidence"], (int, float))
        self.assertIn(data["confidence_band"], ["high", "medium", "low"])

    def test_list_endpoint_includes_confidence_fields(self):
        """List endpoint response includes data_confidence and confidence_band."""
        self.client.force_login(self.user)

        product = Product.objects.create(name="TestProduct", brand=self.brand)
        formulation = Formulation.objects.create(product=product, enrichment_status="complete")
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=1,
            raw_text="Water",
        )

        response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data["results"]), 0)

        for match in data["results"]:
            self.assertIn("data_confidence", match)
            self.assertIn("confidence_band", match)
            self.assertIsInstance(match["data_confidence"], (int, float))
            self.assertIn(match["confidence_band"], ["high", "medium", "low"])

    def test_confidence_rounded_to_2_decimals(self):
        """data_confidence is rounded to 2 decimal places."""
        self.client.force_login(self.user)

        # Create a formulation with 1 of 3 ingredients resolved (0.333...)
        compound = Compound.objects.create(
            canonical_inci="WATER",
            display_name="Water",
        )
        product = Product.objects.create(name="TestProduct", brand=self.brand)
        formulation = Formulation.objects.create(product=product, enrichment_status="complete")

        FormulationIngredient.objects.create(
            formulation=formulation,
            position=1,
            raw_text="Water",
            parse_status="matched",
            compound=compound,
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=2,
            raw_text="Unknown",
            parse_status="unmatched",
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=3,
            raw_text="Ambiguous",
            parse_status="ambiguous",
        )

        response = self.client.post(
            "/api/recommendations/score/",
            {"formulation_id": formulation.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        # 1/3 = 0.333... → 0.33
        self.assertEqual(data["data_confidence"], 0.33)

    def test_ranking_resolves_ties_by_confidence(self):
        """Equal-score formulations are ordered by confidence band (high > medium > low)."""
        self.client.force_login(self.user)

        # Create a resolved formulation (high confidence)
        compound_water = Compound.objects.create(
            canonical_inci="WATER",
            display_name="Water",
        )
        compound_glycerin = Compound.objects.create(
            canonical_inci="GLYCERIN",
            display_name="Glycerin",
        )

        product_high = Product.objects.create(name="Product High Conf", brand=self.brand)
        formulation_high = Formulation.objects.create(product=product_high, enrichment_status="complete")
        FormulationIngredient.objects.create(
            formulation=formulation_high,
            position=1,
            raw_text="Water",
            parse_status="matched",
            compound=compound_water,
        )
        FormulationIngredient.objects.create(
            formulation=formulation_high,
            position=2,
            raw_text="Glycerin",
            parse_status="matched",
            compound=compound_glycerin,
        )

        # Create an unresolved formulation (low confidence)
        product_low = Product.objects.create(name="Product Low Conf", brand=self.brand)
        formulation_low = Formulation.objects.create(product=product_low, enrichment_status="complete")
        FormulationIngredient.objects.create(
            formulation=formulation_low,
            position=1,
            raw_text="Unknown1",
            parse_status="unmatched",
        )

        response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data["results"]

        # Both have score 100, but high-confidence should come first
        high_conf_result = None
        low_conf_result = None
        for result in results:
            if result["product_name"] == "Product High Conf":
                high_conf_result = result
            elif result["product_name"] == "Product Low Conf":
                low_conf_result = result

        self.assertIsNotNone(high_conf_result)
        self.assertIsNotNone(low_conf_result)
        self.assertEqual(high_conf_result["final_score"], 100)
        self.assertEqual(low_conf_result["final_score"], 100)
        self.assertEqual(high_conf_result["confidence_band"], "high")
        self.assertEqual(low_conf_result["confidence_band"], "low")

        # Verify high-confidence comes before low-confidence in list
        high_index = results.index(high_conf_result)
        low_index = results.index(low_conf_result)
        self.assertLess(high_index, low_index)

    def test_score_still_dominates_over_confidence(self):
        """Higher score ranks before lower score, regardless of confidence."""
        self.client.force_login(self.user)

        # Create high-confidence, low-score formulation
        compound = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
        )
        ProfileConstraint.objects.create(
            profile=self.profile,
            kind=ProfileConstraintKind.ALLERGY,
            enforcement=ConstraintEnforcement.PENALIZE,
            severity=ConstraintSeverity.MODERATE,
            compound=compound,
            is_active=True,
        )

        product_low_score = Product.objects.create(
            name="Product Low Score", brand=self.brand
        )
        formulation_low_score = Formulation.objects.create(product=product_low_score, enrichment_status="complete")
        FormulationIngredient.objects.create(
            formulation=formulation_low_score,
            position=1,
            raw_text="Retinol",
            parse_status="matched",
            compound=compound,
        )

        # Create low-confidence, high-score formulation
        product_high_score = Product.objects.create(
            name="Product High Score", brand=self.brand
        )
        formulation_high_score = Formulation.objects.create(product=product_high_score, enrichment_status="complete")
        FormulationIngredient.objects.create(
            formulation=formulation_high_score,
            position=1,
            raw_text="Unknown",
            parse_status="unmatched",
        )

        response = self.client.get("/api/recommendations/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data["results"]

        high_score_result = None
        low_score_result = None
        for result in results:
            if result["product_name"] == "Product High Score":
                high_score_result = result
            elif result["product_name"] == "Product Low Score":
                low_score_result = result

        self.assertIsNotNone(high_score_result)
        self.assertIsNotNone(low_score_result)
        # High score should rank first despite lower confidence
        # (MODERATE penalize = severity weight 8 -> 100 - 8 = 92)
        self.assertEqual(high_score_result["final_score"], 100)
        self.assertEqual(low_score_result["final_score"], 92)

        high_index = results.index(high_score_result)
        low_index = results.index(low_score_result)
        self.assertLess(high_index, low_index)
