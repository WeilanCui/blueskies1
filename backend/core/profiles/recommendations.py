from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from core.models import Formulation, Profile, ProfileConstraint
from core.profiles.constraints import (
    ConstraintEvaluation,
    ConstraintImpact,
    ProfileConstraintEvaluator,
)


@dataclass(frozen=True)
class RecommendationMatch:
    formulation: Formulation
    evaluation: ConstraintEvaluation
    base_score: int
    final_score: int

    @property
    def excluded(self) -> bool:
        return self.evaluation.excluded

    @property
    def warnings(self) -> list[ConstraintImpact]:
        return self.evaluation.warnings

    @property
    def penalties(self) -> list[ConstraintImpact]:
        return self.evaluation.penalties

    @property
    def boosts(self) -> list[ConstraintImpact]:
        return self.evaluation.boosts

    @property
    def matched_constraints(self) -> list[ConstraintImpact]:
        return self.evaluation.matched_constraints

    @property
    def reasons(self) -> list[str]:
        return [match.reason for match in self.matched_constraints]


class RecommendationMatcher:
    """Score and rank formulations against a profile's flexible constraints."""

    def __init__(
        self,
        evaluator: ProfileConstraintEvaluator | None = None,
        extra_evaluators: list | None = None,
    ):
        self.evaluator = evaluator or ProfileConstraintEvaluator()
        self.extra_evaluators = extra_evaluators or []

    def match_formulation(
        self,
        profile: Profile,
        formulation: Formulation,
        *,
        base_score: int = 100,
        constraints: Iterable[ProfileConstraint] | None = None,
        context: dict | None = None,
    ) -> RecommendationMatch:
        evaluation = self.evaluator.evaluate_formulation(
            profile,
            formulation,
            constraints=constraints,
        )

        # Merge impacts from extra evaluators
        for evaluator in self.extra_evaluators:
            extra_impacts = evaluator.evaluate(profile, formulation, context=context)
            for impact in extra_impacts:
                evaluation.matched_constraints.append(impact)

                # Group by enforcement kind
                if impact.enforcement == "warn":
                    evaluation.warnings.append(impact)
                elif impact.enforcement == "penalize":
                    evaluation.penalties.append(impact)
                elif impact.enforcement == "boost":
                    evaluation.boosts.append(impact)
                # "inform" goes to matched_constraints only, not to any group

        return RecommendationMatch(
            formulation=formulation,
            evaluation=evaluation,
            base_score=base_score,
            final_score=self._final_score(base_score, evaluation),
        )

    def rank_formulations(
        self,
        profile: Profile,
        formulations: Iterable[Formulation],
        *,
        base_score: int = 100,
        include_excluded: bool = True,
        constraints: Iterable[ProfileConstraint] | None = None,
    ) -> list[RecommendationMatch]:
        constraints_for_run = (
            list(self.evaluator.active_constraints(profile))
            if constraints is None
            else list(constraints)
        )

        # Prepare context once per run for all evaluators
        context: dict = {}
        for evaluator in self.extra_evaluators:
            if hasattr(evaluator, "prepare"):
                prepare_context = evaluator.prepare(profile)
                if prepare_context is not None:
                    context.update(prepare_context if isinstance(prepare_context, dict) else {"context": prepare_context})

        matches = [
            self.match_formulation(
                profile,
                formulation,
                base_score=base_score,
                constraints=constraints_for_run,
                context=context,
            )
            for formulation in formulations
        ]

        if not include_excluded:
            matches = [match for match in matches if not match.excluded]

        return sorted(
            matches,
            key=lambda match: (
                match.excluded,
                -match.final_score,
                match.formulation.product.name.lower(),
                match.formulation.id,  # pyright: ignore[reportAttributeAccessIssue]
            ),
        )

    def _final_score(
        self,
        base_score: int,
        evaluation: ConstraintEvaluation,
    ) -> int:
        if evaluation.excluded:
            return 0
        return min(100, max(0, base_score + evaluation.score_delta))
