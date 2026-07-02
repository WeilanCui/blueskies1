"""Tests for concern rule evaluation and scoring."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import (
    Brand,
    Compound,
    ChemicalClass,
    ChemicalClassMembership,
    Formulation,
    FormulationIngredient,
    Profile,
    PropertyAssertion,
    PropertyDefinition,
    PropertyDomain,
    SkinProfile,
    ValueType,
)
from core.profiles.recommendations import RecommendationMatcher
from skinconcerns.models import (
    ConcernRule,
    RuleKind,
    RuleTargetType,
    SkinConcern,
    SkinProfileConcern,
)
from skinconcerns.scoring import ConcernRuleEvaluator


class ConcernRuleEvaluatorTests(TestCase):
    """Test concern rule evaluation."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="testuser")
        self.profile = Profile.objects.create(user=self.user)
        self.skin_profile = SkinProfile.objects.create(
            profile=self.profile, is_current=True
        )

        # Create test compounds and chemical classes
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

        # Create test properties
        self.fragrance_property = PropertyDefinition.objects.create(
            key="contains_fragrance",
            domain=PropertyDomain.COMPOUND,
            value_type=ValueType.BOOL,
            label="Contains fragrance",
        )
        PropertyAssertion.objects.create(
            property_def=self.fragrance_property,
            compound=self.retinol,
            value_bool=True,
            is_active=True,
        )

        # Create test products and formulations
        self.brand = Brand.objects.create(name="TestBrand")

        # Formulation with retinol
        self.product_with_retinol = self.brand.products.create(
            name="Retinol Serum",
            category="serum",
        )
        self.formulation_with_retinol = Formulation.objects.create(
            product=self.product_with_retinol,
            raw_inci_text="Water, Retinol",
        )
        FormulationIngredient.objects.create(
            formulation=self.formulation_with_retinol,
            position=1,
            raw_text="Retinol",
            compound=self.retinol,
        )
        FormulationIngredient.objects.create(
            formulation=self.formulation_with_retinol,
            position=2,
            raw_text="Water",
        )

        # Formulation with glycerin
        self.product_with_glycerin = self.brand.products.create(
            name="Hydrating Cream",
            category="moisturizer",
        )
        self.formulation_with_glycerin = Formulation.objects.create(
            product=self.product_with_glycerin,
            raw_inci_text="Water, Glycerin",
        )
        FormulationIngredient.objects.create(
            formulation=self.formulation_with_glycerin,
            position=1,
            raw_text="Glycerin",
            compound=self.glycerin,
        )
        FormulationIngredient.objects.create(
            formulation=self.formulation_with_glycerin,
            position=2,
            raw_text="Water",
        )

        # Create test skin concerns
        self.acne_concern = SkinConcern.objects.create(
            slug="acne",
            display_name="Acne",
            consumer_label="Breakouts",
        )
        self.sensitivity_concern = SkinConcern.objects.create(
            slug="sensitivity",
            display_name="Sensitivity",
            consumer_label="Sensitive skin",
        )

        self.evaluator = ConcernRuleEvaluator()

    def test_penalize_rule_lowers_score(self):
        """PENALIZE rule produces negative delta."""
        rule = ConcernRule.objects.create(
            concern=self.acne_concern,
            key="avoid-retinol",
            label="Avoid Retinol",
            rule_kind=RuleKind.PENALIZE,
            target_type=RuleTargetType.COMPOUND,
            compound=self.retinol,
            weight=10,
            rationale="Retinol can cause irritation.",
        )

        link = SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.acne_concern,
            confidence=1.0,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_retinol, context=context
        )

        self.assertEqual(len(impacts), 1)
        self.assertEqual(impacts[0].enforcement, "penalize")
        self.assertEqual(impacts[0].score_delta, -10)
        self.assertEqual(impacts[0].concern_slug, "acne")
        self.assertEqual(impacts[0].source, "concern")

    def test_negative_seed_weight_still_lowers_score(self):
        """PENALIZE rule with a negative stored weight lowers the score.

        Seed data stores signed weights (e.g. PENALIZE = -10); weight is a
        magnitude and rule_kind controls direction, so a -10 penalize rule
        must still produce a -10 delta (not 0).
        """
        ConcernRule.objects.create(
            concern=self.acne_concern,
            key="avoid-retinol-signed",
            label="Avoid Retinol",
            rule_kind=RuleKind.PENALIZE,
            target_type=RuleTargetType.COMPOUND,
            compound=self.retinol,
            weight=-10,
            rationale="Retinol can cause irritation.",
        )
        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.acne_concern,
            confidence=1.0,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_retinol, context=context
        )

        self.assertEqual(len(impacts), 1)
        self.assertEqual(impacts[0].enforcement, "penalize")
        # A negatively-stored weight must still LOWER the score (the bug was
        # max(weight,0) zeroing it). Exact magnitude varies down the stack as
        # later changes add multipliers, so assert direction, not a value.
        self.assertLess(impacts[0].score_delta, 0)

    def test_boost_rule_raises_score(self):
        """BOOST rule produces positive delta."""
        rule = ConcernRule.objects.create(
            concern=self.sensitivity_concern,
            key="prefer-glycerin",
            label="Prefer Glycerin",
            rule_kind=RuleKind.BOOST,
            target_type=RuleTargetType.COMPOUND,
            compound=self.glycerin,
            weight=10,
            rationale="Glycerin is soothing.",
        )

        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.sensitivity_concern,
            confidence=1.0,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_glycerin, context=context
        )

        self.assertEqual(len(impacts), 1)
        self.assertEqual(impacts[0].enforcement, "boost")
        self.assertEqual(impacts[0].score_delta, 10)

    def test_avoid_rule_warns_and_penalizes(self):
        """AVOID rule produces warning enforcement and negative delta."""
        rule = ConcernRule.objects.create(
            concern=self.acne_concern,
            key="avoid-retinoids",
            label="Avoid Retinoids",
            rule_kind=RuleKind.AVOID,
            target_type=RuleTargetType.CHEMICAL_CLASS,
            chemical_class=self.retinoids,
            weight=10,
            rationale="Retinoids can be irritating.",
        )

        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.acne_concern,
            confidence=1.0,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_retinol, context=context
        )

        self.assertEqual(len(impacts), 1)
        self.assertEqual(impacts[0].enforcement, "warn")
        # AVOID is position-immune: retinol is the last ingredient (factor
        # would be 0.3 if scaled), but the delta stays the full -10 and no
        # position_factor is exposed.
        self.assertEqual(impacts[0].score_delta, -10)
        self.assertIsNone(impacts[0].position_factor)

        # AVOID rules never exclude formulations, only warn and penalize
        match = RecommendationMatcher(extra_evaluators=[ConcernRuleEvaluator()]).match_formulation(
            self.profile, self.formulation_with_retinol
        )
        self.assertFalse(match.excluded)

    def test_refer_rule_informational_only(self):
        """REFER rule produces informational impact with zero delta."""
        rule = ConcernRule.objects.create(
            concern=self.sensitivity_concern,
            key="refer-dermatologist",
            label="Consult dermatologist",
            rule_kind=RuleKind.REFER,
            target_type=RuleTargetType.COMPOUND,
            compound=self.retinol,
            weight=10,
            rationale="Seek professional advice.",
        )

        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.sensitivity_concern,
            confidence=1.0,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_retinol, context=context
        )

        self.assertEqual(len(impacts), 1)
        self.assertEqual(impacts[0].enforcement, "inform")
        self.assertEqual(impacts[0].score_delta, 0)

    def test_recommend_rule_produces_boost_and_coverage(self):
        """RECOMMEND rule matched produces boost impact and is recorded in coverage."""
        rule = ConcernRule.objects.create(
            concern=self.sensitivity_concern,
            key="recommend-glycerin",
            label="Glycerin",
            rule_kind=RuleKind.RECOMMEND,
            target_type=RuleTargetType.COMPOUND,
            compound=self.glycerin,
            weight=10,
            rationale="Great for sensitive skin.",
        )

        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.sensitivity_concern,
            confidence=1.0,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_glycerin, context=context
        )

        # Should have one boost impact
        self.assertEqual(len(impacts), 1)
        self.assertEqual(impacts[0].enforcement, "boost")
        self.assertEqual(impacts[0].score_delta, 10)

        # Should have coverage summary
        self.assertEqual(len(coverage), 1)
        self.assertEqual(coverage[0].concern_slug, "sensitivity")
        self.assertEqual(coverage[0].matched, 1)
        self.assertEqual(coverage[0].total, 1)
        self.assertEqual(list(coverage[0].matched_labels), ["Glycerin"])
        self.assertEqual(list(coverage[0].unmatched_labels), [])

    def test_confidence_scales_delta(self):
        """Confidence 0.5 halves the delta."""
        rule = ConcernRule.objects.create(
            concern=self.acne_concern,
            key="penalize-retinol",
            label="Penalize Retinol",
            rule_kind=RuleKind.PENALIZE,
            target_type=RuleTargetType.COMPOUND,
            compound=self.retinol,
            weight=10,
            rationale="Not ideal.",
        )

        # Create link with lower confidence
        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.acne_concern,
            confidence=0.5,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_retinol, context=context
        )

        self.assertEqual(len(impacts), 1)
        # round(10 * 0.5) = 5, then -5
        self.assertEqual(impacts[0].score_delta, -5)

    def test_inactive_skin_profile_concern_ignored(self):
        """Inactive SkinProfileConcern is skipped."""
        rule = ConcernRule.objects.create(
            concern=self.acne_concern,
            key="penalize-retinol",
            label="Penalize Retinol",
            rule_kind=RuleKind.PENALIZE,
            target_type=RuleTargetType.COMPOUND,
            compound=self.retinol,
            weight=10,
        )

        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.acne_concern,
            is_active=False,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_retinol, context=context
        )

        self.assertEqual(len(impacts), 0)

    def test_inactive_rule_ignored(self):
        """Inactive ConcernRule is skipped."""
        rule = ConcernRule.objects.create(
            concern=self.acne_concern,
            key="penalize-retinol",
            label="Penalize Retinol",
            rule_kind=RuleKind.PENALIZE,
            target_type=RuleTargetType.COMPOUND,
            compound=self.retinol,
            weight=10,
            is_active=False,
        )

        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.acne_concern,
            confidence=1.0,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_retinol, context=context
        )

        self.assertEqual(len(impacts), 0)

    def test_product_category_targeting(self):
        """PENALIZE rule matches product category."""
        rule = ConcernRule.objects.create(
            concern=self.acne_concern,
            key="avoid-serums",
            label="Avoid Serums",
            rule_kind=RuleKind.PENALIZE,
            target_type=RuleTargetType.PRODUCT_CATEGORY,
            product_category="serum",
            weight=10,
        )

        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.acne_concern,
            confidence=1.0,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_retinol, context=context
        )

        self.assertEqual(len(impacts), 1)
        self.assertEqual(impacts[0].enforcement, "penalize")

    def test_product_category_case_insensitive(self):
        """Product category matching is case-insensitive."""
        rule = ConcernRule.objects.create(
            concern=self.acne_concern,
            key="avoid-serums-uppercase",
            label="Avoid Serums",
            rule_kind=RuleKind.PENALIZE,
            target_type=RuleTargetType.PRODUCT_CATEGORY,
            product_category="SERUM",
            weight=10,
        )

        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.acne_concern,
            confidence=1.0,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_retinol, context=context
        )

        self.assertEqual(len(impacts), 1)

    def test_no_concerns_selected_no_impacts(self):
        """Profile with no active concerns produces no impacts."""
        # Don't create any SkinProfileConcern links
        rule = ConcernRule.objects.create(
            concern=self.acne_concern,
            key="penalize-retinol",
            label="Penalize Retinol",
            rule_kind=RuleKind.PENALIZE,
            target_type=RuleTargetType.COMPOUND,
            compound=self.retinol,
            weight=10,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_retinol, context=context
        )

        self.assertEqual(len(impacts), 0)

    def test_no_current_skin_profile_no_impacts(self):
        """Profile with no current skin profile produces no impacts."""
        # Create a new profile with no current skin profile
        new_user = get_user_model().objects.create_user(username="newuser")
        new_profile = Profile.objects.create(user=new_user)

        rule = ConcernRule.objects.create(
            concern=self.acne_concern,
            key="penalize-retinol",
            label="Penalize Retinol",
            rule_kind=RuleKind.PENALIZE,
            target_type=RuleTargetType.COMPOUND,
            compound=self.retinol,
            weight=10,
        )

        context = self.evaluator.prepare(new_profile)
        impacts, coverage = self.evaluator.evaluate(
            new_profile, self.formulation_with_retinol, context=context
        )

        self.assertEqual(len(impacts), 0)

    def test_property_targeting(self):
        """PENALIZE rule matches property target."""
        rule = ConcernRule.objects.create(
            concern=self.sensitivity_concern,
            key="avoid-fragrance",
            label="Avoid Fragrance",
            rule_kind=RuleKind.PENALIZE,
            target_type=RuleTargetType.PROPERTY,
            property_def=self.fragrance_property,
            weight=10,
        )

        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.sensitivity_concern,
            confidence=1.0,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_retinol, context=context
        )

        self.assertEqual(len(impacts), 1)
        self.assertEqual(impacts[0].enforcement, "penalize")

    def test_free_text_targeting(self):
        """PENALIZE rule matches free text target."""
        rule = ConcernRule.objects.create(
            concern=self.sensitivity_concern,
            key="avoid-fragrance-text",
            label="Avoid fragrance",
            rule_kind=RuleKind.PENALIZE,
            target_type=RuleTargetType.FREE_TEXT,
            raw_target="retinol",
            weight=10,
        )

        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.sensitivity_concern,
            confidence=1.0,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_retinol, context=context
        )

        self.assertEqual(len(impacts), 1)
        self.assertEqual(impacts[0].enforcement, "penalize")

    def test_impact_includes_reason_from_rationale(self):
        """Impact reason comes from rule rationale."""
        rule = ConcernRule.objects.create(
            concern=self.acne_concern,
            key="penalize-retinol",
            label="Penalize Retinol",
            rule_kind=RuleKind.PENALIZE,
            target_type=RuleTargetType.COMPOUND,
            compound=self.retinol,
            weight=10,
            rationale="Retinol causes irritation in acne-prone skin.",
        )

        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.acne_concern,
            confidence=1.0,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_retinol, context=context
        )

        self.assertEqual(impacts[0].reason, "Retinol causes irritation in acne-prone skin.")

    def test_impact_includes_default_reason_when_empty(self):
        """Impact uses default reason when rule rationale is empty."""
        rule = ConcernRule.objects.create(
            concern=self.acne_concern,
            key="penalize-retinol",
            label="Penalize Retinol",
            rule_kind=RuleKind.PENALIZE,
            target_type=RuleTargetType.COMPOUND,
            compound=self.retinol,
            weight=10,
            rationale="",
        )

        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.acne_concern,
            confidence=1.0,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_retinol, context=context
        )

        self.assertIn("Related to your concern", impacts[0].reason)
        self.assertIn("Acne", impacts[0].reason)

    def test_partial_recommend_coverage(self):
        """Coverage tracks matched and unmatched RECOMMEND rules."""
        ConcernRule.objects.create(
            concern=self.sensitivity_concern,
            key="recommend-glycerin",
            label="Glycerin",
            rule_kind=RuleKind.RECOMMEND,
            target_type=RuleTargetType.COMPOUND,
            compound=self.glycerin,
            weight=10,
        )
        ConcernRule.objects.create(
            concern=self.sensitivity_concern,
            key="recommend-retinol",
            label="Retinol",
            rule_kind=RuleKind.RECOMMEND,
            target_type=RuleTargetType.COMPOUND,
            compound=self.retinol,
            weight=10,
        )

        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.sensitivity_concern,
            confidence=1.0,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_glycerin, context=context
        )

        # Only glycerin matches
        self.assertEqual(len(coverage), 1)
        self.assertEqual(coverage[0].matched, 1)
        self.assertEqual(coverage[0].total, 2)
        self.assertEqual(list(coverage[0].matched_labels), ["Glycerin"])
        self.assertEqual(list(coverage[0].unmatched_labels), ["Retinol"])

    def test_zero_match_recommend_coverage(self):
        """Coverage reports zero matches with full total."""
        ConcernRule.objects.create(
            concern=self.sensitivity_concern,
            key="recommend-glycerin",
            label="Glycerin",
            rule_kind=RuleKind.RECOMMEND,
            target_type=RuleTargetType.COMPOUND,
            compound=self.glycerin,
            weight=10,
        )

        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.sensitivity_concern,
            confidence=1.0,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_retinol, context=context
        )

        # Nothing matches, but coverage is still reported
        self.assertEqual(len(coverage), 1)
        self.assertEqual(coverage[0].matched, 0)
        self.assertEqual(coverage[0].total, 1)
        self.assertEqual(list(coverage[0].matched_labels), [])
        self.assertEqual(list(coverage[0].unmatched_labels), ["Glycerin"])

    def test_concern_without_recommend_rules_omitted(self):
        """Concern with no RECOMMEND rules produces no coverage."""
        ConcernRule.objects.create(
            concern=self.sensitivity_concern,
            key="penalize-retinol",
            label="Avoid Retinol",
            rule_kind=RuleKind.PENALIZE,
            target_type=RuleTargetType.COMPOUND,
            compound=self.retinol,
            weight=10,
        )

        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.sensitivity_concern,
            confidence=1.0,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_retinol, context=context
        )

        # No coverage entry for concerns without RECOMMEND rules
        self.assertEqual(len(coverage), 0)

    def test_recommend_unmatched_not_penalized(self):
        """Unmatched RECOMMEND rules produce no negative delta."""
        ConcernRule.objects.create(
            concern=self.sensitivity_concern,
            key="recommend-glycerin",
            label="Glycerin",
            rule_kind=RuleKind.RECOMMEND,
            target_type=RuleTargetType.COMPOUND,
            compound=self.glycerin,
            weight=10,
        )

        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.sensitivity_concern,
            confidence=1.0,
        )

        context = self.evaluator.prepare(self.profile)
        impacts, coverage = self.evaluator.evaluate(
            self.profile, self.formulation_with_retinol, context=context
        )

        # No impacts (unmatched RECOMMEND produces no impact)
        self.assertEqual(len(impacts), 0)
        # But coverage is still tracked
        self.assertEqual(len(coverage), 1)
        self.assertEqual(coverage[0].matched, 0)

    def test_matched_recommend_boosts_score(self):
        """Product with matched RECOMMEND rule scores higher than without."""
        ConcernRule.objects.create(
            concern=self.sensitivity_concern,
            key="recommend-glycerin",
            label="Glycerin",
            rule_kind=RuleKind.RECOMMEND,
            target_type=RuleTargetType.COMPOUND,
            compound=self.glycerin,
            weight=10,
        )

        SkinProfileConcern.objects.create(
            skin_profile=self.skin_profile,
            concern=self.sensitivity_concern,
            confidence=1.0,
        )

        context = self.evaluator.prepare(self.profile)

        # Product with glycerin (matches RECOMMEND)
        impacts_with, coverage_with = self.evaluator.evaluate(
            self.profile, self.formulation_with_glycerin, context=context
        )
        score_with = sum(i.score_delta for i in impacts_with)

        # Product without glycerin (no match)
        impacts_without, coverage_without = self.evaluator.evaluate(
            self.profile, self.formulation_with_retinol, context=context
        )
        score_without = sum(i.score_delta for i in impacts_without)

        # With glycerin should score higher
        self.assertGreater(score_with, score_without)
