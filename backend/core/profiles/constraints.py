from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from core.models import (
    ConstraintEnforcement,
    ConstraintSeverity,
    Formulation,
    Profile,
    ProfileConstraint,
)
from core.profiles.matching import (
    MatchResult,
    matches_chemical_class,
    matches_compound,
    matches_property,
    matches_raw_label,
    position_factor,
)


SEVERITY_WEIGHTS = {
    ConstraintSeverity.LOW: 3,
    ConstraintSeverity.MODERATE: 8,
    ConstraintSeverity.HIGH: 15,
    ConstraintSeverity.CRITICAL: 100,
}


@dataclass(frozen=True)
class ConstraintImpact:
    constraint_id: int
    kind: str
    enforcement: str
    severity: str
    target_type: str
    target: str
    reason: str
    score_delta: int
    source: str = "constraint"
    concern_slug: str | None = None
    position_factor: float | None = None


@dataclass
class ConstraintEvaluation:
    excluded: bool = False
    warnings: list[ConstraintImpact] = field(default_factory=list)
    penalties: list[ConstraintImpact] = field(default_factory=list)
    boosts: list[ConstraintImpact] = field(default_factory=list)
    matched_constraints: list[ConstraintImpact] = field(default_factory=list)

    @property
    def score_delta(self) -> int:
        return sum(match.score_delta for match in self.matched_constraints)


class ProfileConstraintEvaluator:
    """Evaluate flexible profile constraints against formulations."""

    def evaluate_formulation(
        self,
        profile: Profile,
        formulation: Formulation,
        constraints: Iterable[ProfileConstraint] | None = None,
    ) -> ConstraintEvaluation:
        evaluation = ConstraintEvaluation()
        active_constraints = (
            self.active_constraints(profile) if constraints is None else constraints
        )

        for constraint in active_constraints:
            match_result = self._matches_formulation(constraint, formulation)
            if not match_result.matched:
                continue

            impact = self._impact_for_constraint(constraint, match_result)
            evaluation.matched_constraints.append(impact)

            if constraint.enforcement == ConstraintEnforcement.EXCLUDE:
                evaluation.excluded = True
                evaluation.warnings.append(impact)
            elif constraint.enforcement == ConstraintEnforcement.WARN:
                evaluation.warnings.append(impact)
            elif constraint.enforcement == ConstraintEnforcement.PENALIZE:
                evaluation.penalties.append(impact)
            elif constraint.enforcement == ConstraintEnforcement.BOOST:
                evaluation.boosts.append(impact)

        return evaluation

    def active_constraints(self, profile: Profile):
        return profile.constraints.filter(is_active=True).select_related(  # pyright: ignore[reportAttributeAccessIssue]
            "compound",
            "chemical_class",
            "formulation",
            "property_def",
        )

    def _matches_formulation(
        self,
        constraint: ProfileConstraint,
        formulation: Formulation,
    ) -> MatchResult:
        if constraint.formulation_id:  # pyright: ignore[reportAttributeAccessIssue]
            matched = constraint.formulation_id == formulation.id  # pyright: ignore[reportAttributeAccessIssue]
            return MatchResult(matched=matched, best_position=None, total_ingredients=None)

        if constraint.compound_id:  # pyright: ignore[reportAttributeAccessIssue]
            return matches_compound(
                formulation, constraint.compound_id  # pyright: ignore[reportAttributeAccessIssue]
            )

        if constraint.chemical_class_id:  # pyright: ignore[reportAttributeAccessIssue]
            return matches_chemical_class(
                formulation, constraint.chemical_class_id  # pyright: ignore[reportAttributeAccessIssue]
            )

        if constraint.property_def_id:  # pyright: ignore[reportAttributeAccessIssue]
            return matches_property(
                formulation, constraint.property_def_id  # pyright: ignore[reportAttributeAccessIssue]
            )

        if constraint.raw_label:
            return matches_raw_label(formulation, constraint.raw_label)

        return MatchResult(matched=False, best_position=None, total_ingredients=None)


    def _impact_for_constraint(
        self,
        constraint: ProfileConstraint,
        match_result: MatchResult | None = None,
    ) -> ConstraintImpact:
        score_delta, pos_factor = self._score_delta(constraint, match_result)
        target = constraint.display_target()
        return ConstraintImpact(
            constraint_id=constraint.id,  # pyright: ignore[reportAttributeAccessIssue]
            kind=constraint.kind,
            enforcement=constraint.enforcement,
            severity=constraint.severity,
            target_type=constraint.target_type,
            target=target,
            reason=self._reason(constraint, target),
            score_delta=score_delta,
            position_factor=pos_factor,
        )

    def _score_delta(
        self,
        constraint: ProfileConstraint,
        match_result: MatchResult | None = None,
    ) -> tuple[int, float | None]:
        """Compute score delta and position factor for a constraint.

        Returns:
            Tuple of (score_delta, position_factor).
            position_factor is None for non-ingredient targets or safety signals.
        """
        base_weight = SEVERITY_WEIGHTS[constraint.severity]
        weighted = round(base_weight * constraint.confidence)

        # Determine if position_factor applies: ingredient-targeted + scalable enforcement
        pos_factor = None
        is_ingredient_target = constraint.target_type in ("compound", "chemical_class")
        is_scalable_enforcement = constraint.enforcement in (
            ConstraintEnforcement.PENALIZE,
            ConstraintEnforcement.BOOST,
        )

        if is_ingredient_target and is_scalable_enforcement and match_result:
            pos_factor = position_factor(match_result)

        if constraint.enforcement == ConstraintEnforcement.EXCLUDE:
            return (-100, None)  # EXCLUDE never scales
        if constraint.enforcement == ConstraintEnforcement.PENALIZE:
            delta = -weighted
            if pos_factor is not None:
                delta = round(delta * pos_factor)
            return (delta, pos_factor)
        if constraint.enforcement == ConstraintEnforcement.BOOST:
            delta = max(1, weighted)
            if pos_factor is not None:
                delta = max(1, round(delta * pos_factor))
            return (delta, pos_factor)
        return (0, None)

    def _reason(self, constraint: ProfileConstraint, target: str) -> str:
        if constraint.enforcement == ConstraintEnforcement.EXCLUDE:
            return f"Excluded because it matches your {constraint.kind}: {target}."
        if constraint.enforcement == ConstraintEnforcement.WARN:
            return f"Caution because it matches your {constraint.kind}: {target}."
        if constraint.enforcement == ConstraintEnforcement.PENALIZE:
            return f"Lower match because it conflicts with your {constraint.kind}: {target}."
        if constraint.enforcement == ConstraintEnforcement.BOOST:
            return f"Higher match because it supports your {constraint.kind}: {target}."
        return f"Matched your {constraint.kind}: {target}."


def evaluate_formulation_constraints(
    profile: Profile,
    formulation: Formulation,
) -> ConstraintEvaluation:
    return ProfileConstraintEvaluator().evaluate_formulation(profile, formulation)
