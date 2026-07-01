from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models

from skinconcerns.models.choices import (
    ConcernGroup,
    ConcernType,
    CopyMode,
    RecommendationPolicy,
)

if TYPE_CHECKING:
    from django.db.models import Manager

    from skinconcerns.models.alias import ConcernAlias
    from skinconcerns.models.evidence import ConcernEvidence
    from skinconcerns.models.referral_trigger import ConcernReferralTrigger
    from skinconcerns.models.rule import ConcernRule
    from skinconcerns.models.skin_profile_concern import SkinProfileConcern


class SkinConcern(models.Model):
    """Canonical concern definition owned by the skin concern bounded context."""

    id: int
    aliases: Manager[ConcernAlias]
    rules: Manager[ConcernRule]
    evidence_links: Manager[ConcernEvidence]
    referral_triggers: Manager[ConcernReferralTrigger]
    profile_selections: Manager[SkinProfileConcern]

    slug = models.SlugField(max_length=128, unique=True)
    display_name = models.CharField(max_length=128)
    consumer_label = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    group = models.CharField(
        max_length=32,
        choices=ConcernGroup.choices,
        default=ConcernGroup.BREAKOUTS,
    )
    concern_type = models.CharField(
        max_length=32,
        choices=ConcernType.choices,
        default=ConcernType.COSMETIC,
    )
    recommendation_policy = models.CharField(
        max_length=32,
        choices=RecommendationPolicy.choices,
        default=RecommendationPolicy.ALLOW,
    )
    copy_mode = models.CharField(
        max_length=16,
        choices=CopyMode.choices,
        default=CopyMode.NORMAL,
    )
    is_common = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["group", "display_name"]
        indexes = [
            models.Index(fields=["group", "is_common", "is_active"]),
            models.Index(fields=["concern_type", "recommendation_policy"]),
        ]

    def __str__(self) -> str:
        return self.display_name
