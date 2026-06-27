from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.db.models import Q
from django.db.models.query import QuerySet

from core.models import SkinProfile
from skinconcerns.models import (
    ConcernGroup,
    ConcernReferralTrigger,
    ProfileConcernSource,
    RecommendationPolicy,
    SkinConcern,
    SkinProfileConcern,
)
from skinconcerns.normalization import normalize_search_text


GROUP_ORDER = [choice[0] for choice in ConcernGroup.choices]


@dataclass(frozen=True)
class ResolvedConcern:
    concern: SkinConcern
    raw_text: str
    confidence: float


class ConcernSearchService:
    """Search concern labels, aliases, and safety trigger phrases."""

    def active_concerns(self) -> QuerySet[SkinConcern]:
        return (
            SkinConcern.objects.filter(is_active=True)
            .prefetch_related("aliases", "referral_triggers")
            .order_by("group", "display_name")
        )

    def grouped_common(self) -> list[dict]:
        concerns = list(self.active_concerns().filter(is_common=True))
        groups = []
        for group, label in ConcernGroup.choices:
            group_concerns = [concern for concern in concerns if concern.group == group]
            if group_concerns:
                groups.append(
                    {
                        "group": group,
                        "label": label,
                        "concerns": group_concerns,
                    }
                )
        return groups

    def search(self, query: str, *, limit: int = 12) -> list[SkinConcern]:
        term = query.strip()
        if not term:
            return []

        normalized = normalize_search_text(term)
        active = self.active_concerns()
        exact_matches = list(
            active.filter(
                Q(slug=term)
                | Q(slug=normalized.replace(" ", "_"))
                | Q(aliases__normalized_alias=normalized, aliases__is_active=True)
                | Q(
                    referral_triggers__normalized_trigger=normalized,
                    referral_triggers__is_active=True,
                )
            ).distinct()
        )
        fuzzy_matches = list(
            active.filter(
                Q(slug__icontains=term)
                | Q(display_name__icontains=term)
                | Q(consumer_label__icontains=term)
                | Q(description__icontains=term)
                | Q(aliases__alias_text__icontains=term, aliases__is_active=True)
                | Q(
                    aliases__normalized_alias__icontains=normalized,
                    aliases__is_active=True,
                )
                | Q(
                    referral_triggers__trigger_text__icontains=term,
                    referral_triggers__is_active=True,
                )
                | Q(
                    referral_triggers__normalized_trigger__icontains=normalized,
                    referral_triggers__is_active=True,
                )
            )
            .exclude(id__in=[concern.id for concern in exact_matches])
            .distinct()
        )
        return [*exact_matches, *fuzzy_matches][:limit]


class ConcernResolutionService:
    """Resolve selected slugs or free text into canonical concerns."""

    def __init__(self, search_service: ConcernSearchService | None = None):
        self.search_service = search_service or ConcernSearchService()

    def resolve_terms(self, terms: Iterable[str]) -> list[ResolvedConcern]:
        resolved: dict[int, ResolvedConcern] = {}
        for raw in terms:
            raw_text = str(raw).strip()
            if not raw_text:
                continue

            exact = self._exact_match(raw_text)
            if exact is not None:
                resolved[exact.id] = ResolvedConcern(exact, raw_text, 1.0)
                continue

            matches = self.search_service.search(raw_text, limit=1)
            if matches:
                concern = matches[0]
                resolved.setdefault(
                    concern.id,
                    ResolvedConcern(concern, raw_text, 0.7),
                )

        return list(resolved.values())

    def referral_triggers_for_text(self, text: str) -> list[ConcernReferralTrigger]:
        normalized = normalize_search_text(text)
        if not normalized:
            return []
        triggers = ConcernReferralTrigger.objects.filter(is_active=True).select_related(
            "concern"
        )
        return [
            trigger
            for trigger in triggers
            if trigger.normalized_trigger
            and trigger.normalized_trigger in normalized
        ]

    def _exact_match(self, raw_text: str) -> SkinConcern | None:
        normalized = normalize_search_text(raw_text)
        concern = SkinConcern.objects.filter(
            Q(slug=raw_text)
            | Q(slug=normalized.replace(" ", "_"))
            | Q(aliases__normalized_alias=normalized, aliases__is_active=True),
            is_active=True,
        ).first()
        return concern


class ConcernPolicyService:
    """Aggregate concern routing into a recommendation policy."""

    POLICY_RANK = {
        RecommendationPolicy.ALLOW: 0,
        RecommendationPolicy.ALLOW_WITH_CLAIM_LIMITS: 1,
        RecommendationPolicy.SUPPORTIVE_ONLY: 2,
        RecommendationPolicy.SUPPRESS: 3,
    }

    def policy_for_concerns(self, concerns: Iterable[SkinConcern]) -> dict:
        concern_list = list(concerns)
        if not concern_list:
            return {
                "recommendation_policy": RecommendationPolicy.ALLOW,
                "copy_mode": "normal",
                "recommendation_allowed": True,
                "supportive_only": False,
                "refer_out": False,
            }

        strictest = max(
            concern_list,
            key=lambda concern: self.POLICY_RANK[concern.recommendation_policy],
        )
        policy = strictest.recommendation_policy
        return {
            "recommendation_policy": policy,
            "copy_mode": strictest.copy_mode,
            "recommendation_allowed": policy
            in {
                RecommendationPolicy.ALLOW,
                RecommendationPolicy.ALLOW_WITH_CLAIM_LIMITS,
                RecommendationPolicy.SUPPORTIVE_ONLY,
            },
            "supportive_only": policy == RecommendationPolicy.SUPPORTIVE_ONLY,
            "refer_out": policy == RecommendationPolicy.SUPPRESS,
        }


class ConcernSelectionService:
    """Write normalized selected/detected concerns for a skin profile."""

    def __init__(
        self,
        resolution_service: ConcernResolutionService | None = None,
    ):
        self.resolution_service = resolution_service or ConcernResolutionService()

    def set_skin_profile_concerns(
        self,
        skin_profile: SkinProfile,
        terms: Iterable[str],
        *,
        source: str = ProfileConcernSource.USER_SELECTED,
    ) -> list[SkinProfileConcern]:
        resolved = self.resolution_service.resolve_terms(terms)
        selected_ids = [item.concern.id for item in resolved]

        active = SkinProfileConcern.objects.filter(
            skin_profile=skin_profile,
            is_active=True,
        )
        if selected_ids:
            active.exclude(concern_id__in=selected_ids).update(is_active=False)
        else:
            active.update(is_active=False)

        selections = []
        for item in resolved:
            selection, _ = SkinProfileConcern.objects.update_or_create(
                skin_profile=skin_profile,
                concern=item.concern,
                defaults={
                    "source": source,
                    "confidence": item.confidence,
                    "raw_text": item.raw_text,
                    "is_active": True,
                },
            )
            selections.append(selection)

        return selections

    def active_for_skin_profile(self, skin_profile: SkinProfile):
        return skin_profile.active_concern_selections()
