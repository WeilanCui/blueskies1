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
    matches_chemical_class,
    matches_compound,
    matches_property,
    matches_raw_label,
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
            if not self._matches_formulation(constraint, formulation):
                continue

            impact = self._impact_for_constraint(constraint)
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
    ) -> bool:
        if constraint.formulation_id:  # pyright: ignore[reportAttributeAccessIssue]
            return constraint.formulation_id == formulation.id  # pyright: ignore[reportAttributeAccessIssue]

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

        return False


    def _impact_for_constraint(
        self,
        constraint: ProfileConstraint,
    ) -> ConstraintImpact:
        score_delta = self._score_delta(constraint)
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
        )

    def _score_delta(self, constraint: ProfileConstraint) -> int:
        base_weight = SEVERITY_WEIGHTS[constraint.severity]
        weighted = round(base_weight * constraint.confidence)

        if constraint.enforcement == ConstraintEnforcement.EXCLUDE:
            return -100
        if constraint.enforcement == ConstraintEnforcement.PENALIZE:
            return -weighted
        if constraint.enforcement == ConstraintEnforcement.BOOST:
            return max(1, weighted)
        return 0

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
