from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable

from core.models import Formulation, Profile, ProfileConstraint
from core.profiles.constraints import (
    ConstraintEvaluation,
    ConstraintImpact,
    ProfileConstraintEvaluator,
)

if TYPE_CHECKING:
    from skinconcerns.scoring import CoverageSummary


@dataclass(frozen=True)
class RecommendationMatch:
    formulation: Formulation
    evaluation: ConstraintEvaluation
    base_score: int
    final_score: int
    coverage: list[CoverageSummary] = field(default_factory=list)  # pyright: ignore[reportGeneralTypeIssues]

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
        contexts: dict[int, object] | None = None,
    ) -> RecommendationMatch:
        evaluation = self.evaluator.evaluate_formulation(
            profile,
            formulation,
            constraints=constraints,
        )

        # Merge impacts from extra evaluators. Contexts are namespaced by
        # evaluator index so multiple evaluators' prepare() results never
        # collide under a shared key.
        coverage_list = []
        for index, evaluator in enumerate(self.extra_evaluators):
            evaluator_context = None if contexts is None else contexts.get(index)
            result = evaluator.evaluate(
                profile, formulation, context=evaluator_context
            )
            # Handle both old-style (list of impacts) and new-style (tuple of impacts, coverage)
            if isinstance(result, tuple):
                extra_impacts, extra_coverage = result
                coverage_list.extend(extra_coverage)
            else:
                extra_impacts = result

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
            coverage=coverage_list,
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

        # Prepare per-evaluator context once per run, namespaced by index so
        # one evaluator's context can never clobber another's.
        contexts: dict[int, object] = {}
        for index, evaluator in enumerate(self.extra_evaluators):
            if hasattr(evaluator, "prepare"):
                contexts[index] = evaluator.prepare(profile)

        matches = [
            self.match_formulation(
                profile,
                formulation,
                base_score=base_score,
                constraints=constraints_for_run,
                contexts=contexts,
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
