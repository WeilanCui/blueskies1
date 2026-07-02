"""Concern rule scoring and evaluation."""

from django.db.models import Prefetch

from core.models import Formulation, Profile
from core.profiles.matching import (
    matches_chemical_class,
    matches_compound,
    matches_product_category,
    matches_property,
    matches_raw_label,
)
from core.profiles.constraints import ConstraintImpact
from skinconcerns.models import RuleTargetType, ConcernRule


class ConcernRuleEvaluator:
    """Evaluate concern rules and produce scoring impacts."""

    def prepare(self, profile: Profile):
        """Prepare context: resolve active concerns and rules once per run."""
        skin_profile = profile.current_skin_profile
        if not skin_profile:
            return {}

        # Prefetch active rules for each concern to avoid N+1 queries
        active_rules_prefetch = Prefetch(
            "concern__rules",
            queryset=ConcernRule.objects.filter(is_active=True),
            to_attr="active_rules",
        )

        # Get active SkinProfileConcern rows with concerns and rules prefetched
        active_links = skin_profile.concerns.filter(is_active=True).select_related(
            "concern"
        ).prefetch_related(active_rules_prefetch)

        # Build list of (concern, confidence, rules)
        concerns_data = []
        for link in active_links:
            concern = link.concern
            # Read prefetched active rules
            active_rules = concern.active_rules
            concerns_data.append((concern, link.confidence, list(active_rules)))

        return {"concerns_data": concerns_data}

    def evaluate(
        self, profile: Profile, formulation: Formulation, context: dict | None = None
    ) -> list[ConstraintImpact]:
        """Evaluate concern rules against formulation; return list of impacts."""
        if context is None:
            context = self.prepare(profile)

        impacts = []
        concerns_data = context.get("concerns_data", [])

        for concern, link_confidence, rules in concerns_data:
            for rule in rules:
                # Check if rule target matches formulation
                if not self._matches_rule_target(rule, formulation):
                    continue

                # Calculate delta
                delta = round(rule.weight * link_confidence)

                # Determine enforcement and score_delta based on rule kind
                if rule.rule_kind == "penalize":
                    enforcement = "penalize"
                    score_delta = -delta
                elif rule.rule_kind == "boost":
                    enforcement = "boost"
                    score_delta = max(1, delta)
                elif rule.rule_kind == "avoid":
                    enforcement = "warn"
                    score_delta = -delta
                elif rule.rule_kind in ("refer", "recommend"):
                    enforcement = "inform"
                    score_delta = 0
                else:
                    continue

                # Build reason
                if rule.rationale:
                    reason = rule.rationale
                else:
                    reason = f"Related to your concern: {concern.display_name}"

                impact = ConstraintImpact(
                    constraint_id=rule.id,
                    kind=rule.rule_kind,
                    enforcement=enforcement,
                    severity="moderate",
                    target_type=rule.target_type,
                    target=rule.label,
                    reason=reason,
                    score_delta=score_delta,
                    source="concern",
                    concern_slug=concern.slug,
                )
                impacts.append(impact)

        return impacts

    def _matches_rule_target(self, rule, formulation: Formulation) -> bool:
        """Check if rule target matches formulation."""
        target_type = rule.target_type

        if target_type == RuleTargetType.COMPOUND:
            if not rule.compound_id:
                return False
            return matches_compound(formulation, rule.compound_id)

        if target_type == RuleTargetType.CHEMICAL_CLASS:
            if not rule.chemical_class_id:
                return False
            return matches_chemical_class(formulation, rule.chemical_class_id)

        if target_type == RuleTargetType.PROPERTY:
            if not rule.property_def_id:
                return False
            return matches_property(formulation, rule.property_def_id)

        if target_type == RuleTargetType.FREE_TEXT:
            if not rule.raw_target or not rule.raw_target.strip():
                return False
            return matches_raw_label(formulation, rule.raw_target)

        if target_type == RuleTargetType.PRODUCT_CATEGORY:
            if not rule.product_category or not rule.product_category.strip():
                return False
            return matches_product_category(formulation, rule.product_category)

        return False
