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
from skinconcerns.models import RuleTargetType, ConcernRule, ConcernEvidence

# Evidence type weights for multiplier calculation
EVIDENCE_TYPE_WEIGHTS = {
    "clinical": 0.15,
    "regulatory": 0.12,
    "safety": 0.12,
    "public_guidance": 0.08,
    "rule": 0.05,
    "definition": 0.05,
}

# Multiplier bounds
EVIDENCE_MULT_MIN = 0.6
EVIDENCE_MULT_MAX = 1.3


def evidence_multiplier(rule: ConcernRule) -> tuple[float, int]:
    """
    Compute evidence multiplier for a rule based on its active evidence.

    Only counts rule-scoped evidence, not concern-scoped evidence.
    Deduplicates by distinct literature_reference_id (each reference counts its type weight once).
    Consumes prefetch cache to avoid additional database queries.

    Returns:
        Tuple of (multiplier, evidence_count) where:
        - multiplier: float in [0.6, 1.3]
        - evidence_count: int number of distinct references
    """
    # Deduplicate by literature_reference_id, taking max weight per reference
    # Iterate over prefetched cache (rule.evidence_links.all() hits cache, not DB)
    refs_weights = {}
    for evidence in rule.evidence_links.all():
        # Filter in Python so both the prefetched path (already active-only)
        # and direct calls on non-prefetched rules exclude inactive rows.
        if not evidence.is_active:
            continue
        ref_id = evidence.literature_reference_id
        evidence_type = evidence.evidence_type
        weight = EVIDENCE_TYPE_WEIGHTS.get(evidence_type, 0.0)

        # If this ref already seen, keep the max weight
        if ref_id in refs_weights:
            refs_weights[ref_id] = max(refs_weights[ref_id], weight)
        else:
            refs_weights[ref_id] = weight

    # Compute multiplier: clamp(0.6 + sum(weights), 0.6, 1.3)
    total_weight = sum(refs_weights.values())
    multiplier = round(
        max(EVIDENCE_MULT_MIN, min(EVIDENCE_MULT_MAX, EVIDENCE_MULT_MIN + total_weight)),
        4,
    )
    evidence_count = len(refs_weights)

    return multiplier, evidence_count


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

        # Prefetch active rules with their evidence links for evidence multiplier computation
        evidence_prefetch = Prefetch(
            "evidence_links",
            queryset=ConcernEvidence.objects.filter(is_active=True),
        )
        active_rules_prefetch = Prefetch(
            "concern__rules",
            queryset=ConcernRule.objects.filter(is_active=True).prefetch_related(evidence_prefetch),
            to_attr="active_rules",
        )

        # Get active SkinProfileConcern rows with concerns and rules prefetched
        active_links = skin_profile.concerns.filter(is_active=True).select_related(
            "concern"
        ).prefetch_related(active_rules_prefetch)

        # Build list of (concern, confidence, rules) and compute evidence multipliers
        concerns_data = []
        rule_multipliers = {}  # Cache multipliers: rule_id -> (multiplier, evidence_count)

        for link in active_links:
            concern = link.concern
            # Read prefetched active rules
            active_rules = concern.active_rules

            # Precompute evidence multiplier for each rule
            for rule in active_rules:
                if rule.id not in rule_multipliers:
                    rule_multipliers[rule.id] = evidence_multiplier(rule)

            concerns_data.append((concern, link.confidence, list(active_rules)))

        return {"concerns_data": concerns_data, "rule_multipliers": rule_multipliers}

    def evaluate(
        self, profile: Profile, formulation: Formulation, context: dict | None = None
    ) -> tuple[list[ConstraintImpact], list[CoverageSummary]]:
        """Evaluate concern rules against formulation; return list of impacts and coverage summaries."""
        if context is None:
            context = self.prepare(profile)

        impacts = []
        coverage_summaries = []
        concerns_data = context.get("concerns_data", [])
        rule_multipliers = context.get("rule_multipliers", {})

        for concern, link_confidence, rules in concerns_data:
            matched_labels = []
            unmatched_labels = []

            for rule in rules:
                # Check if rule target matches formulation
                match_result = self._matches_rule_target(rule, formulation)

                # Get evidence multiplier for this rule
                evidence_mult, evidence_count = rule_multipliers.get(rule.id, (EVIDENCE_MULT_MIN, 0))

                # Position factor applies only to dose-dependent kinds on
                # ingredient targets. AVOID/REFER are position-immune (safety /
                # informational signals must not fade with concentration).
                pos_factor = None
                needs_position_factor = (
                    rule.rule_kind in ("penalize", "boost", "recommend")
                    and rule.target_type
                    in (RuleTargetType.COMPOUND, RuleTargetType.CHEMICAL_CLASS)
                )

                # Compute delta with single round: all multiplicative factors,
                # then round, then sign/floor. `weight` is a magnitude — its
                # sign in seed data is incidental (PENALIZE stores -10); the
                # rule_kind below controls direction, so take abs().
                base_multiplier = abs(rule.weight) * link_confidence * evidence_mult
                if match_result.matched and needs_position_factor:
                    pos_factor = position_factor(match_result)
                    base_multiplier = base_multiplier * pos_factor

                delta = round(base_multiplier)

                # Determine enforcement and score_delta based on rule kind
                score_delta = 0
                enforcement = None

                if rule.rule_kind == "penalize":
                    if match_result.matched:
                        enforcement = "penalize"
                        score_delta = -delta
                    else:
                        continue
                elif rule.rule_kind == "boost":
                    if match_result.matched:
                        enforcement = "boost"
                        score_delta = max(1, delta)
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
                    evidence_count=evidence_count,
                    evidence_multiplier=evidence_mult,
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
