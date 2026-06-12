from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import (
    ChemicalClass,
    ChemicalClassMembership,
    Compound,
    ConstraintEnforcement,
    ConstraintSeverity,
    Formulation,
    FormulationIngredient,
    Profile,
    ProfileConstraint,
    ProfileConstraintKind,
    PropertyAssertion,
    PropertyDefinition,
    PropertyDomain,
    SkinProfile,
    ValueType,
)
from core.models.brand import Brand
from core.models.product import Product
from core.profiles import ProfileConstraintEvaluator, RecommendationMatcher


class ProfileConstraintModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alex")
        self.profile = Profile.objects.create(user=self.user, handle="alex")
        self.compound = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
        )
        self.chemical_class = ChemicalClass.objects.create(
            name="Retinoids",
            slug="retinoids",
        )

    def test_constraint_requires_a_target(self):
        constraint = ProfileConstraint(profile=self.profile)

        with self.assertRaises(ValidationError):
            constraint.full_clean()

    def test_constraint_allows_raw_label_fallback(self):
        constraint = ProfileConstraint(
            profile=self.profile,
            raw_label="blue tansy",
            kind=ProfileConstraintKind.SENSITIVITY,
        )

        constraint.full_clean()
        self.assertEqual(constraint.target_type, "text")

    def test_constraint_allows_only_one_normalized_target(self):
        constraint = ProfileConstraint(
            profile=self.profile,
            compound=self.compound,
            chemical_class=self.chemical_class,
            raw_label="retinoids",
        )

        with self.assertRaises(ValidationError):
            constraint.full_clean()

    def test_only_one_current_skin_profile_per_profile(self):
        SkinProfile.objects.create(profile=self.profile, label="Summer", is_current=True)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SkinProfile.objects.create(
                    profile=self.profile,
                    label="Winter",
                    is_current=True,
                )


class ProfileConstraintEvaluatorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="morgan")
        self.profile = Profile.objects.create(user=self.user, handle="morgan")
        self.retinoids = ChemicalClass.objects.create(
            name="Retinoids",
            slug="retinoids",
        )
        self.retinol = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
        )
        self.glycerin = Compound.objects.create(
            canonical_inci="GLYCERIN",
            display_name="Glycerin",
        )
        ChemicalClassMembership.objects.create(
            compound=self.retinol,
            chemical_class=self.retinoids,
            is_active=True,
        )
        self.brand = Brand.objects.create(name="Blueskies")
        self.product = Product.objects.create(
            name="Night Renewal Serum",
            brand=self.brand,
        )
        self.formulation = Formulation.objects.create(
            product=self.product,
            raw_inci_text="Water, Glycerin, Retinol",
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
            compound=self.glycerin,
        )
        FormulationIngredient.objects.create(
            formulation=self.formulation,
            position=3,
            raw_text="Retinol",
            compound=self.retinol,
        )
        self.evaluator = ProfileConstraintEvaluator()

    def test_excludes_formulation_for_compound_constraint(self):
        ProfileConstraint.objects.create(
            profile=self.profile,
            kind=ProfileConstraintKind.ALLERGY,
            enforcement=ConstraintEnforcement.EXCLUDE,
            severity=ConstraintSeverity.CRITICAL,
            compound=self.retinol,
        )

        evaluation = self.evaluator.evaluate_formulation(
            self.profile,
            self.formulation,
        )

        self.assertTrue(evaluation.excluded)
        self.assertEqual(evaluation.score_delta, -100)
        self.assertEqual(evaluation.matched_constraints[0].target, "RETINOL")

    def test_warns_for_chemical_class_constraint(self):
        ProfileConstraint.objects.create(
            profile=self.profile,
            kind=ProfileConstraintKind.SENSITIVITY,
            enforcement=ConstraintEnforcement.WARN,
            severity=ConstraintSeverity.MODERATE,
            chemical_class=self.retinoids,
        )

        evaluation = self.evaluator.evaluate_formulation(
            self.profile,
            self.formulation,
        )

        self.assertFalse(evaluation.excluded)
        self.assertEqual(len(evaluation.warnings), 1)
        self.assertEqual(evaluation.warnings[0].target_type, "chemical_class")

    def test_penalizes_for_property_constraint(self):
        property_def = PropertyDefinition.objects.create(
            key="fragrance_allergen",
            domain=PropertyDomain.COMPOUND,
            value_type=ValueType.BOOL,
            label="Fragrance allergen",
            description="Flags fragrance allergens for sensitive users.",
        )
        PropertyAssertion.objects.create(
            property_def=property_def,
            compound=self.retinol,
            value_bool=True,
            is_active=True,
        )
        ProfileConstraint.objects.create(
            profile=self.profile,
            kind=ProfileConstraintKind.AVOID,
            enforcement=ConstraintEnforcement.PENALIZE,
            severity=ConstraintSeverity.HIGH,
            confidence=0.5,
            property_def=property_def,
        )

        evaluation = self.evaluator.evaluate_formulation(
            self.profile,
            self.formulation,
        )

        self.assertFalse(evaluation.excluded)
        self.assertEqual(len(evaluation.penalties), 1)
        self.assertEqual(evaluation.score_delta, -8)

    def test_boosts_for_raw_label_constraint(self):
        ProfileConstraint.objects.create(
            profile=self.profile,
            kind=ProfileConstraintKind.PREFER,
            enforcement=ConstraintEnforcement.BOOST,
            severity=ConstraintSeverity.LOW,
            raw_label="glycerin",
        )

        evaluation = self.evaluator.evaluate_formulation(
            self.profile,
            self.formulation,
        )

        self.assertFalse(evaluation.excluded)
        self.assertEqual(len(evaluation.boosts), 1)
        self.assertGreater(evaluation.score_delta, 0)

    def test_explicit_empty_constraint_list_evaluates_no_rules(self):
        ProfileConstraint.objects.create(
            profile=self.profile,
            kind=ProfileConstraintKind.ALLERGY,
            enforcement=ConstraintEnforcement.EXCLUDE,
            severity=ConstraintSeverity.CRITICAL,
            compound=self.retinol,
        )

        evaluation = self.evaluator.evaluate_formulation(
            self.profile,
            self.formulation,
            constraints=[],
        )

        self.assertFalse(evaluation.excluded)
        self.assertEqual(evaluation.matched_constraints, [])


class RecommendationMatcherTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="riley")
        self.profile = Profile.objects.create(user=self.user, handle="riley")
        self.retinol = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
        )
        self.glycerin = Compound.objects.create(
            canonical_inci="GLYCERIN",
            display_name="Glycerin",
        )
        self.brand = Brand.objects.create(name="Blueskies")
        self.safe_product = Product.objects.create(
            name="Barrier Cream",
            brand=self.brand,
        )
        self.safe_formulation = Formulation.objects.create(
            product=self.safe_product,
            raw_inci_text="Water, Glycerin",
        )
        FormulationIngredient.objects.create(
            formulation=self.safe_formulation,
            position=1,
            raw_text="Glycerin",
            compound=self.glycerin,
        )
        self.excluded_product = Product.objects.create(
            name="Retinol Night Cream",
            brand=self.brand,
        )
        self.excluded_formulation = Formulation.objects.create(
            product=self.excluded_product,
            raw_inci_text="Water, Glycerin, Retinol",
        )
        FormulationIngredient.objects.create(
            formulation=self.excluded_formulation,
            position=1,
            raw_text="Glycerin",
            compound=self.glycerin,
        )
        FormulationIngredient.objects.create(
            formulation=self.excluded_formulation,
            position=2,
            raw_text="Retinol",
            compound=self.retinol,
        )
        ProfileConstraint.objects.create(
            profile=self.profile,
            kind=ProfileConstraintKind.ALLERGY,
            enforcement=ConstraintEnforcement.EXCLUDE,
            severity=ConstraintSeverity.CRITICAL,
            compound=self.retinol,
        )
        ProfileConstraint.objects.create(
            profile=self.profile,
            kind=ProfileConstraintKind.PREFER,
            enforcement=ConstraintEnforcement.BOOST,
            severity=ConstraintSeverity.LOW,
            compound=self.glycerin,
        )
        self.matcher = RecommendationMatcher()

    def test_match_formulation_returns_score_and_reasons(self):
        match = self.matcher.match_formulation(
            self.profile,
            self.safe_formulation,
            base_score=90,
        )

        self.assertFalse(match.excluded)
        self.assertEqual(match.final_score, 93)
        self.assertEqual(len(match.boosts), 1)
        self.assertIn("Higher match", match.reasons[0])

    def test_rank_formulations_keeps_excluded_items_by_default(self):
        matches = self.matcher.rank_formulations(
            self.profile,
            [self.excluded_formulation, self.safe_formulation],
            base_score=90,
        )

        self.assertEqual([match.formulation for match in matches], [
            self.safe_formulation,
            self.excluded_formulation,
        ])
        self.assertTrue(matches[1].excluded)
        self.assertEqual(matches[1].final_score, 0)

    def test_rank_formulations_can_hide_excluded_items(self):
        matches = self.matcher.rank_formulations(
            self.profile,
            [self.excluded_formulation, self.safe_formulation],
            include_excluded=False,
        )

        self.assertEqual([match.formulation for match in matches], [
            self.safe_formulation,
        ])
