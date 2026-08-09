"""Tests for ingredient position weighting in matching and scoring."""

from django.contrib.auth.models import User
from django.test import TestCase

from core.models import (
    Brand,
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
    Product,
)
from core.profiles.matching import (
    MatchResult,
    matches_chemical_class,
    matches_compound,
    matches_property,
    matches_raw_label,
    position_factor,
)
from core.profiles.constraints import ProfileConstraintEvaluator


class PositionFactorMathTests(TestCase):
    """Test the position_factor formula."""

    def test_position_1_top_of_list(self):
        """Position 1 should yield factor 1.0."""
        result = MatchResult(matched=True, best_position=1, total_ingredients=10)
        factor = position_factor(result)
        self.assertAlmostEqual(factor, 1.0)

    def test_last_position_gets_floor(self):
        """Last position in multi-ingredient list should yield 0.3."""
        result = MatchResult(matched=True, best_position=10, total_ingredients=10)
        factor = position_factor(result)
        self.assertAlmostEqual(factor, 0.3, places=2)

    def test_single_ingredient_list(self):
        """Single-ingredient list should yield 1.0 regardless of position."""
        result = MatchResult(matched=True, best_position=1, total_ingredients=1)
        factor = position_factor(result)
        self.assertAlmostEqual(factor, 1.0)

    def test_missing_position_data(self):
        """Missing position or total should fallback to 1.0."""
        # Missing best_position
        result = MatchResult(matched=True, best_position=None, total_ingredients=10)
        self.assertAlmostEqual(position_factor(result), 1.0)

        # Missing total_ingredients
        result = MatchResult(matched=True, best_position=1, total_ingredients=None)
        self.assertAlmostEqual(position_factor(result), 1.0)

        # Both missing
        result = MatchResult(matched=True, best_position=None, total_ingredients=None)
        self.assertAlmostEqual(position_factor(result), 1.0)

    def test_not_matched_returns_neutral(self):
        """Unmatched result should return 1.0."""
        result = MatchResult(matched=False, best_position=None, total_ingredients=None)
        self.assertAlmostEqual(position_factor(result), 1.0)

    def test_middle_position(self):
        """Position 5 in a 10-ingredient list."""
        result = MatchResult(matched=True, best_position=5, total_ingredients=10)
        # factor = max(0.3, 1.0 - 0.7 * (5-1) / (10-1))
        # = max(0.3, 1.0 - 0.7 * 4/9)
        # = max(0.3, 1.0 - 0.311)
        # ≈ 0.689
        factor = position_factor(result)
        expected = max(0.3, 1.0 - 0.7 * 4 / 9)
        self.assertAlmostEqual(factor, expected, places=3)

    def test_best_position_wins_in_multi_match(self):
        """When multiple ingredients match, use the best (lowest) position."""
        # Simulating chemical class matching positions 3 and 30
        result = MatchResult(matched=True, best_position=3, total_ingredients=30)
        factor = position_factor(result)
        # Should use position 3, not 30
        # factor = max(0.3, 1.0 - 0.7 * (3-1) / (30-1))
        # = max(0.3, 1.0 - 0.7 * 2/29)
        # ≈ 0.952
        expected = max(0.3, 1.0 - 0.7 * 2 / 29)
        self.assertAlmostEqual(factor, expected, places=3)


class MatchingWithPositionTests(TestCase):
    """Test matching functions returning MatchResult with position data."""

    def setUp(self):
        self.brand = Brand.objects.create(name="TestBrand")
        self.product = Product.objects.create(name="TestProduct", brand=self.brand)

        self.retinol = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
        )
        self.glycerin = Compound.objects.create(
            canonical_inci="GLYCERIN",
            display_name="Glycerin",
        )
        self.retinoids = ChemicalClass.objects.create(
            name="Retinoids",
            slug="retinoids",
        )
        ChemicalClassMembership.objects.create(
            compound=self.retinol,
            chemical_class=self.retinoids,
            is_active=True,
        )

    def test_matches_compound_returns_position(self):
        """matches_compound should return best position."""
        formulation = Formulation.objects.create(
            product=self.product,
            raw_inci_text="Water, Retinol, Glycerin",
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=1,
            raw_text="Water",
            compound=None,
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=2,
            raw_text="Retinol",
            compound=self.retinol,
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=3,
            raw_text="Glycerin",
            compound=self.glycerin,
        )

        result = matches_compound(formulation, self.retinol.id)

        self.assertTrue(result.matched)
        self.assertEqual(result.best_position, 2)
        self.assertEqual(result.total_ingredients, 3)

    def test_matches_compound_no_match(self):
        """matches_compound should return not matched with no position."""
        formulation = Formulation.objects.create(
            product=self.product,
            raw_inci_text="Water, Glycerin",
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=1,
            raw_text="Water",
            compound=None,
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=2,
            raw_text="Glycerin",
            compound=self.glycerin,
        )

        result = matches_compound(formulation, self.retinol.id)

        self.assertFalse(result.matched)
        self.assertIsNone(result.best_position)
        self.assertIsNone(result.total_ingredients)

    def test_matches_chemical_class_returns_best_position(self):
        """matches_chemical_class should return best position among matches."""
        formulation = Formulation.objects.create(
            product=self.product,
            raw_inci_text="Water, OtherRetinoid, Glycerin, Retinol",
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=1,
            raw_text="Water",
            compound=None,
        )
        # Another retinoid at position 2
        other_retinoid = Compound.objects.create(
            canonical_inci="RETINYL_PALMITATE",
            display_name="Retinyl Palmitate",
        )
        ChemicalClassMembership.objects.create(
            compound=other_retinoid,
            chemical_class=self.retinoids,
            is_active=True,
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=2,
            raw_text="OtherRetinoid",
            compound=other_retinoid,
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=3,
            raw_text="Glycerin",
            compound=self.glycerin,
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=4,
            raw_text="Retinol",
            compound=self.retinol,
        )

        result = matches_chemical_class(formulation, self.retinoids.id)

        self.assertTrue(result.matched)
        self.assertEqual(result.best_position, 2)  # Best position among retinoids
        self.assertEqual(result.total_ingredients, 4)

    def test_matches_property_no_position(self):
        """matches_property should not return position data."""
        formulation = Formulation.objects.create(
            product=self.product,
            raw_inci_text="Water, Retinol",
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=1,
            raw_text="Water",
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=2,
            raw_text="Retinol",
            compound=self.retinol,
        )

        result = matches_property(formulation, 99)  # Non-existent property

        self.assertFalse(result.matched)
        self.assertIsNone(result.best_position)
        self.assertIsNone(result.total_ingredients)

    def test_matches_raw_label_no_position(self):
        """matches_raw_label should not return position data."""
        formulation = Formulation.objects.create(
            product=self.product,
            raw_inci_text="Water, Retinol",
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=1,
            raw_text="Water",
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=2,
            raw_text="Retinol",
            compound=self.retinol,
        )

        result = matches_raw_label(formulation, "Water")

        self.assertTrue(result.matched)
        self.assertIsNone(result.best_position)
        self.assertIsNone(result.total_ingredients)


class ConstraintScoringWithPositionTests(TestCase):
    """Test constraint scoring with position weighting."""

    def setUp(self):
        self.user = User.objects.create_user(username="alex")
        self.profile = Profile.objects.create(user=self.user, handle="alex")

        self.brand = Brand.objects.create(name="TestBrand")
        self.product = Product.objects.create(name="TestProduct", brand=self.brand)

        self.retinol = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
        )
        self.glycerin = Compound.objects.create(
            canonical_inci="GLYCERIN",
            display_name="Glycerin",
        )

    def test_penalize_trace_ingredient_smaller_delta(self):
        """Trace ingredient (near end) should receive smaller penalty."""
        # Create formulation with Retinol at position 20 (near end)
        formulation_trace = Formulation.objects.create(
            product=self.product,
            raw_inci_text="Water, " + ", ".join([f"Ingredient{i}" for i in range(2, 20)]) + ", Retinol",
        )
        FormulationIngredient.objects.create(
            formulation=formulation_trace,
            position=1,
            raw_text="Water",
        )
        for i in range(2, 20):
            FormulationIngredient.objects.create(
                formulation=formulation_trace,
                position=i,
                raw_text=f"Ingredient{i}",
            )
        FormulationIngredient.objects.create(
            formulation=formulation_trace,
            position=20,
            raw_text="Retinol",
            compound=self.retinol,
        )

        # Create formulation with Retinol at position 2 (near top)
        formulation_headline = Formulation.objects.create(
            product=self.product,
            raw_inci_text="Water, Retinol, " + ", ".join([f"Ingredient{i}" for i in range(3, 20)]),
        )
        FormulationIngredient.objects.create(
            formulation=formulation_headline,
            position=1,
            raw_text="Water",
        )
        FormulationIngredient.objects.create(
            formulation=formulation_headline,
            position=2,
            raw_text="Retinol",
            compound=self.retinol,
        )
        for i in range(3, 20):
            FormulationIngredient.objects.create(
                formulation=formulation_headline,
                position=i,
                raw_text=f"Ingredient{i}",
            )

        # Create a PENALIZE constraint
        constraint = ProfileConstraint.objects.create(
            profile=self.profile,
            compound=self.retinol,
            kind=ProfileConstraintKind.SENSITIVITY,
            enforcement=ConstraintEnforcement.PENALIZE,
            severity=ConstraintSeverity.MODERATE,
            confidence=1.0,
        )

        evaluator = ProfileConstraintEvaluator()
        eval_trace = evaluator.evaluate_formulation(self.profile, formulation_trace)
        eval_headline = evaluator.evaluate_formulation(self.profile, formulation_headline)

        # Both should have penalties, but trace penalty should be smaller (less negative)
        trace_penalty = eval_trace.penalties[0].score_delta if eval_trace.penalties else 0
        headline_penalty = eval_headline.penalties[0].score_delta if eval_headline.penalties else 0

        # Both should be negative (penalties)
        self.assertLess(trace_penalty, 0)
        self.assertLess(headline_penalty, 0)

        # Trace penalty should be strictly smaller (closer to 0, less negative)
        self.assertGreater(trace_penalty, headline_penalty)

        # Check that position_factor was computed
        if eval_trace.penalties:
            self.assertIsNotNone(eval_trace.penalties[0].position_factor)
            self.assertLess(eval_trace.penalties[0].position_factor, 1.0)

    def test_exclude_ignores_position(self):
        """EXCLUDE constraint should not be scaled by position."""
        formulation = Formulation.objects.create(
            product=self.product,
            raw_inci_text="Water, " + ", ".join([f"Ingredient{i}" for i in range(2, 20)]) + ", Retinol",
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=1,
            raw_text="Water",
        )
        for i in range(2, 20):
            FormulationIngredient.objects.create(
                formulation=formulation,
                position=i,
                raw_text=f"Ingredient{i}",
            )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=20,
            raw_text="Retinol",
            compound=self.retinol,
        )

        constraint = ProfileConstraint.objects.create(
            profile=self.profile,
            compound=self.retinol,
            kind=ProfileConstraintKind.SENSITIVITY,
            enforcement=ConstraintEnforcement.EXCLUDE,
            severity=ConstraintSeverity.CRITICAL,
            confidence=1.0,
        )

        evaluator = ProfileConstraintEvaluator()
        evaluation = evaluator.evaluate_formulation(self.profile, formulation)

        # Should be excluded
        self.assertTrue(evaluation.excluded)

        # EXCLUDE must emit its warning impact regardless of position
        self.assertEqual(len(evaluation.warnings), 1)
        impact = evaluation.warnings[0]
        # EXCLUDE delta should be -100, unscaled
        self.assertEqual(impact.score_delta, -100)
        # position_factor should be None for EXCLUDE
        self.assertIsNone(impact.position_factor)

    def test_non_ingredient_target_no_position_factor(self):
        """Non-ingredient targets (raw_label) should not have position_factor."""
        formulation = Formulation.objects.create(
            product=self.product,
            raw_inci_text="Water, Retinol",
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=1,
            raw_text="Water",
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=2,
            raw_text="Retinol",
            compound=self.retinol,
        )

        constraint = ProfileConstraint.objects.create(
            profile=self.profile,
            raw_label="Water",
            kind=ProfileConstraintKind.SENSITIVITY,
            enforcement=ConstraintEnforcement.PENALIZE,
            severity=ConstraintSeverity.MODERATE,
            confidence=1.0,
        )

        evaluator = ProfileConstraintEvaluator()
        evaluation = evaluator.evaluate_formulation(self.profile, formulation)

        # The raw-label constraint must actually produce a penalty
        self.assertEqual(len(evaluation.penalties), 1)
        impact = evaluation.penalties[0]
        # Raw label targets should have no position_factor
        self.assertIsNone(impact.position_factor)

    def test_boost_applies_position_factor(self):
        """BOOST constraint should scale by position_factor."""
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
            compound=self.glycerin,
        )

        constraint = ProfileConstraint.objects.create(
            profile=self.profile,
            compound=self.glycerin,
            kind=ProfileConstraintKind.GOAL_SUPPORT,
            enforcement=ConstraintEnforcement.BOOST,
            severity=ConstraintSeverity.MODERATE,
            confidence=1.0,
        )

        evaluator = ProfileConstraintEvaluator()
        evaluation = evaluator.evaluate_formulation(self.profile, formulation)

        # Should have a boost
        self.assertTrue(len(evaluation.boosts) > 0)
        impact = evaluation.boosts[0]

        # Position 2 out of 2 = last → position_factor ≈ 0.3
        # base_weight = 8, confidence = 1.0 → weighted = 8
        # scaled = max(1, round(8 * 0.3)) = max(1, 2) = 2
        self.assertAlmostEqual(impact.position_factor, 0.3, places=2)
        self.assertIn(impact.score_delta, [2, 3])  # Allow for rounding variations
