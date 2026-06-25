from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from django.db.models import Q

from core.models import (
    ConstraintEnforcement,
    ConstraintSeverity,
    Formulation,
    Profile,
    ProfileConstraint,
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
            return formulation.ingredients.filter(  # pyright: ignore[reportAttributeAccessIssue]
                compound_id=constraint.compound_id,  # pyright: ignore[reportAttributeAccessIssue]
            ).exists()

        if constraint.chemical_class_id:  # pyright: ignore[reportAttributeAccessIssue]
            return formulation.ingredients.filter(  # pyright: ignore[reportAttributeAccessIssue]
                compound__chemical_class_memberships__chemical_class_id=(
                    constraint.chemical_class_id  # pyright: ignore[reportAttributeAccessIssue]
                ),
                compound__chemical_class_memberships__is_active=True,
            ).exists()

        if constraint.property_def_id:  # pyright: ignore[reportAttributeAccessIssue]
            return self._matches_property_constraint(constraint, formulation)

        if constraint.raw_label:
            return self._matches_raw_label(constraint.raw_label, formulation)

        return False

    def _matches_property_constraint(
        self,
        constraint: ProfileConstraint,
        formulation: Formulation,
    ) -> bool:
        property_def_id = constraint.property_def_id  # pyright: ignore[reportAttributeAccessIssue]
        return Formulation.objects.filter(pk=formulation.pk).filter(
            Q(
                property_assertions__property_def_id=property_def_id,
                property_assertions__is_active=True,
            )
            | Q(
                ingredients__compound__property_assertions__property_def_id=(
                    property_def_id
                ),
                ingredients__compound__property_assertions__is_active=True,
            )
            | Q(
                ingredients__compound__chemical_class_memberships__is_active=True,
                ingredients__compound__chemical_class_memberships__chemical_class__property_assertions__property_def_id=property_def_id,
                ingredients__compound__chemical_class_memberships__chemical_class__property_assertions__is_active=True,
            )
        ).exists()

    def _matches_raw_label(self, raw_label: str, formulation: Formulation) -> bool:
        label = raw_label.strip()
        if not label:
            return False

        return Formulation.objects.filter(pk=formulation.pk).filter(
            Q(product__name__icontains=label)
            | Q(product__brand__name__icontains=label)
            | Q(version_label__icontains=label)
            | Q(market__icontains=label)
            | Q(made_in__icontains=label)
            | Q(barcode__icontains=label)
            | Q(raw_inci_text__icontains=label)
            | Q(ingredients__raw_text__icontains=label)
            | Q(ingredients__compound__canonical_inci__icontains=label)
            | Q(ingredients__compound__display_name__icontains=label)
        ).exists()

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
