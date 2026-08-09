"""Concern rule scoring and evaluation."""

from dataclasses import dataclass

from django.db.models import Prefetch

from core.models import Formulation, Profile
from core.profiles.matching import (
    MatchResult,
    matches_chemical_class,
    matches_compound,
    matches_product_category,
    matches_property,
    matches_raw_label,
    position_factor,
)
from core.profiles.constraints import ConstraintImpact
from skinconcerns.models import RuleTargetType, ConcernRule


@dataclass(frozen=True)
class CoverageSummary:
    """Coverage summary for a concern's RECOMMEND rules."""

    concern_slug: str
    concern_label: str
    matched_labels: tuple[str, ...] | list[str]
    unmatched_labels: tuple[str, ...] | list[str]
    matched: int
    total: int


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
    ) -> tuple[list[ConstraintImpact], list[CoverageSummary]]:
        """Evaluate concern rules against formulation; return list of impacts and coverage summaries."""
        if context is None:
            context = self.prepare(profile)

        impacts = []
        coverage_summaries = []
        concerns_data = context.get("concerns_data", [])

        for concern, link_confidence, rules in concerns_data:
            matched_labels = []
            unmatched_labels = []

            for rule in rules:
                # Check if rule target matches formulation
                match_result = self._matches_rule_target(rule, formulation)

                # Calculate delta. `weight` is a magnitude — its sign in seed
                # data is incidental (e.g. PENALIZE stores -10); `rule_kind`
                # alone controls the direction below, so take the magnitude.
                delta = round(abs(rule.weight) * link_confidence)

                # Determine enforcement and score_delta based on rule kind
                pos_factor = None
                score_delta = 0
                enforcement = None

                if rule.rule_kind == "penalize":
                    if match_result.matched:
                        enforcement = "penalize"
                        score_delta = -delta
                        # Apply position_factor for ingredient-targeted PENALIZE
                        if rule.target_type in (RuleTargetType.COMPOUND, RuleTargetType.CHEMICAL_CLASS):
                            pos_factor = position_factor(match_result)
                            score_delta = round(score_delta * pos_factor)
                    else:
                        continue
                elif rule.rule_kind == "boost":
                    if match_result.matched:
                        enforcement = "boost"
                        score_delta = max(1, delta)
                        # Apply position_factor for ingredient-targeted BOOST
                        if rule.target_type in (RuleTargetType.COMPOUND, RuleTargetType.CHEMICAL_CLASS):
                            pos_factor = position_factor(match_result)
                            score_delta = max(1, round(score_delta * pos_factor))
                    else:
                        continue
                elif rule.rule_kind == "avoid":
                    if match_result.matched:
                        enforcement = "warn"
                        # AVOID is a safety caution: its warning and its delta
                        # are position-immune (a trace amount you must avoid is
                        # still worth avoiding). pos_factor stays None.
                        score_delta = -delta
                    else:
                        continue
                elif rule.rule_kind == "refer":
                    if match_result.matched:
                        enforcement = "inform"
                        score_delta = 0
                    else:
                        continue
                elif rule.rule_kind == "recommend":
                    # RECOMMEND rules: track coverage
                    if match_result.matched:
                        matched_labels.append(rule.label)
                        # Matched RECOMMEND produces boost impact
                        enforcement = "boost"
                        score_delta = max(1, delta)
                        # Apply position_factor for ingredient-targeted RECOMMEND
                        if rule.target_type in (RuleTargetType.COMPOUND, RuleTargetType.CHEMICAL_CLASS):
                            pos_factor = position_factor(match_result)
                            score_delta = max(1, round(score_delta * pos_factor))
                    else:
                        unmatched_labels.append(rule.label)
                        continue
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
                    position_factor=pos_factor,
                )
                impacts.append(impact)

            # Aggregate coverage for RECOMMEND rules (if any)
            recommend_rules = [r for r in rules if r.rule_kind == "recommend"]
            if recommend_rules:  # Only emit coverage if concern has RECOMMEND rules
                total = len(recommend_rules)
                matched = len(matched_labels)
                coverage = CoverageSummary(
                    concern_slug=concern.slug,
                    concern_label=concern.consumer_label,
                    matched_labels=tuple(matched_labels),
                    unmatched_labels=tuple(unmatched_labels),
                    matched=matched,
                    total=total,
                )
                coverage_summaries.append(coverage)

        return impacts, coverage_summaries

    def _matches_rule_target(self, rule, formulation: Formulation) -> MatchResult:
        """Check if rule target matches formulation.

        Returns:
            MatchResult with matched status and position data if applicable.
        """
        target_type = rule.target_type

        if target_type == RuleTargetType.COMPOUND:
            if not rule.compound_id:
                return MatchResult(matched=False, best_position=None, total_ingredients=None)
            return matches_compound(formulation, rule.compound_id)

        if target_type == RuleTargetType.CHEMICAL_CLASS:
            if not rule.chemical_class_id:
                return MatchResult(matched=False, best_position=None, total_ingredients=None)
            return matches_chemical_class(formulation, rule.chemical_class_id)

        if target_type == RuleTargetType.PROPERTY:
            if not rule.property_def_id:
                return MatchResult(matched=False, best_position=None, total_ingredients=None)
            return matches_property(formulation, rule.property_def_id)

        if target_type == RuleTargetType.FREE_TEXT:
            if not rule.raw_target or not rule.raw_target.strip():
                return MatchResult(matched=False, best_position=None, total_ingredients=None)
            return matches_raw_label(formulation, rule.raw_target)

        if target_type == RuleTargetType.PRODUCT_CATEGORY:
            if not rule.product_category or not rule.product_category.strip():
                return MatchResult(matched=False, best_position=None, total_ingredients=None)
            return matches_product_category(formulation, rule.product_category)

        return MatchResult(matched=False, best_position=None, total_ingredients=None)
