from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from core.models import Profile, SkinProfile
from skinconcerns.models import (
    ConcernAlias,
    ConcernEvidence,
    ConcernReferralTrigger,
    ConcernRule,
    EvidenceType,
    RecommendationPolicy,
    RuleTargetType,
    SkinConcern,
    SkinProfileConcern,
    TriggerSeverity,
)
from skinconcerns.normalization import normalize_search_text
from skinconcerns.seeds.loader import seed_skin_concerns
from skinconcerns.services import (
    ConcernPolicyService,
    ConcernResolutionService,
    ConcernSearchService,
)


class SkinConcernModelTests(TestCase):
    def setUp(self):
        self.concern = SkinConcern.objects.create(
            slug="breakouts",
            display_name="Breakouts",
            consumer_label="Breakouts",
        )

    def test_alias_normalizes_and_is_unique(self):
        alias = ConcernAlias.objects.create(
            concern=self.concern,
            alias_text="Zits!",
        )

        self.assertEqual(alias.normalized_alias, "zits")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ConcernAlias.objects.create(
                    concern=self.concern,
                    alias_text="zits",
                )

    def test_concern_rule_requires_matching_single_target(self):
        missing_target = ConcernRule(
            concern=self.concern,
            key="missing-target",
            label="Missing target",
            target_type=RuleTargetType.PRODUCT_CATEGORY,
        )

        with self.assertRaises(ValidationError):
            missing_target.full_clean()

        too_many_targets = ConcernRule(
            concern=self.concern,
            key="too-many-targets",
            label="Too many targets",
            target_type=RuleTargetType.PRODUCT_CATEGORY,
            product_category="cleanser",
            raw_target="retinoids",
        )

        with self.assertRaises(ValidationError):
            too_many_targets.full_clean()

        with self.assertRaises(ValidationError):
            ConcernRule.objects.create(
                concern=self.concern,
                key="missing-target-db",
                label="Missing target",
                target_type=RuleTargetType.PRODUCT_CATEGORY,
            )

        with self.assertRaises(ValidationError):
            ConcernRule.objects.create(
                concern=self.concern,
                key="too-many-targets-db",
                label="Too many targets",
                target_type=RuleTargetType.PRODUCT_CATEGORY,
                product_category="cleanser",
                raw_target="retinoids",
            )

    def test_skin_profile_concern_is_unique_per_active_profile_concern(self):
        user = get_user_model().objects.create_user(username="alex")
        profile = Profile.objects.create(user=user)
        skin_profile = SkinProfile.objects.create(profile=profile)
        SkinProfileConcern.objects.create(
            skin_profile=skin_profile,
            concern=self.concern,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SkinProfileConcern.objects.create(
                    skin_profile=skin_profile,
                    concern=self.concern,
                )

    def test_concern_policy_for_loaded_selections_does_not_query(self):
        medical_adjacent = SkinConcern.objects.create(
            slug="eczema_like_patches",
            display_name="Eczema-like patches",
            consumer_label="Dry, itchy patches",
            recommendation_policy=RecommendationPolicy.SUPPORTIVE_ONLY,
        )
        user = get_user_model().objects.create_user(username="taylor")
        profile = Profile.objects.create(user=user)
        skin_profile = SkinProfile.objects.create(profile=profile)
        SkinProfileConcern.objects.create(
            skin_profile=skin_profile,
            concern=self.concern,
        )
        SkinProfileConcern.objects.create(
            skin_profile=skin_profile,
            concern=medical_adjacent,
        )
        selections = list(skin_profile.active_concern_selections())

        with self.assertNumQueries(0):
            policy = skin_profile.concern_policy_for_selections(selections)

        self.assertEqual(
            policy["recommendation_policy"],
            RecommendationPolicy.SUPPORTIVE_ONLY,
        )


class SkinConcernSeedAndServiceTests(TestCase):
    def setUp(self):
        seed_skin_concerns()

    def test_seed_includes_required_v1_concerns(self):
        required = {
            "breakouts",
            "blackheads",
            "whiteheads",
            "clogged_pores",
            "oiliness",
            "dryness",
            "barrier_damage",
            "sensitive_skin",
            "redness",
            "eczema_like_patches",
            "seborrheic_flakes",
            "psoriasis_like_scaling",
            "dark_spots",
            "uneven_tone",
            "dullness",
            "rough_texture",
            "razor_bumps",
            "sun_protection",
            "rash_safety",
            "changing_bleeding_mole",
        }

        seeded = set(SkinConcern.objects.values_list("slug", flat=True))

        self.assertFalse(required - seeded)

    def test_seed_includes_key_search_aliases(self):
        aliases = set(ConcernAlias.objects.values_list("normalized_alias", flat=True))

        for alias in [
            "zits",
            "pimples",
            "acne",
            "eczema",
            "rosacea",
            "flaky",
            "rash",
            "melasma",
        ]:
            self.assertIn(normalize_search_text(alias), aliases)

    def test_search_resolves_common_and_medical_terms(self):
        search = ConcernSearchService()

        self.assertEqual(search.search("zits")[0].slug, "breakouts")
        self.assertEqual(search.search("eczema")[0].slug, "eczema_like_patches")
        self.assertEqual(search.search("rosacea")[0].slug, "redness")
        self.assertEqual(search.search("rosácea")[0].slug, "redness")
        self.assertEqual(search.search("flaky")[0].slug, "dryness")
        self.assertEqual(search.search("rash")[0].slug, "rash_safety")
        self.assertEqual(search.search("melasma")[0].slug, "melasma_like_pigmentation")

    def test_melasma_search_uses_supportive_only_policy(self):
        concern = ConcernSearchService().search("melasma")[0]

        policy = ConcernPolicyService().policy_for_concerns([concern])

        self.assertEqual(
            policy["recommendation_policy"],
            RecommendationPolicy.SUPPORTIVE_ONLY,
        )
        self.assertTrue(policy["supportive_only"])

    def test_new_changing_spot_referral_trigger_matches_free_text(self):
        triggers = ConcernResolutionService().referral_triggers_for_text(
            "I noticed a new changing spot near my cheek."
        )

        self.assertIn(
            "new-changing-spot",
            {trigger.key for trigger in triggers},
        )

    def test_referral_trigger_detection_uses_phrase_boundaries(self):
        reopen_sores_triggers = ConcernResolutionService().referral_triggers_for_text(
            "Please reopen sores clinic hours."
        )
        bleeding_mole_triggers = ConcernResolutionService().referral_triggers_for_text(
            "My bleeding molecules research is unrelated."
        )
        thrash_triggers = ConcernResolutionService().referral_triggers_for_text(
            "I only listen to thrash metal."
        )

        self.assertNotIn(
            "open-sores",
            {trigger.key for trigger in reopen_sores_triggers},
        )
        self.assertNotIn(
            "bleeding-mole",
            {trigger.key for trigger in bleeding_mole_triggers},
        )
        self.assertEqual(thrash_triggers, [])

    def test_referral_trigger_detection_ignores_negated_phrases(self):
        triggers = ConcernResolutionService().referral_triggers_for_text(
            "No painful rash and not a bleeding mole."
        )

        self.assertEqual(triggers, [])

        positive_triggers = ConcernResolutionService().referral_triggers_for_text(
            "I do have a painful rash."
        )

        self.assertIn(
            "painful-rash",
            {trigger.key for trigger in positive_triggers},
        )

    def test_policy_service_uses_strictest_concern_policy(self):
        concerns = SkinConcern.objects.filter(
            slug__in=["breakouts", "eczema_like_patches", "rash_safety"]
        )

        policy = ConcernPolicyService().policy_for_concerns(concerns)

        self.assertEqual(policy["recommendation_policy"], RecommendationPolicy.SUPPRESS)
        self.assertTrue(policy["refer_out"])
        self.assertFalse(policy["supportive_only"])

    def test_seed_deactivates_removed_catalog_entries(self):
        concern = SkinConcern.objects.get(slug="dark_spots")
        stale_concern = SkinConcern.objects.create(
            slug="obsolete_concern",
            display_name="Obsolete concern",
            consumer_label="Obsolete concern",
        )
        stale_alias = ConcernAlias.objects.create(
            concern=concern,
            alias_text="obsolete alias",
        )
        stale_rule = ConcernRule.objects.create(
            concern=concern,
            key="obsolete-rule",
            label="Obsolete rule",
            target_type=RuleTargetType.FREE_TEXT,
            raw_target="obsolete target",
        )
        stale_evidence = ConcernEvidence.objects.create(
            concern=concern,
            key="obsolete-evidence",
            source_name="Obsolete source",
            citation_label="Obsolete citation",
            evidence_type=EvidenceType.PUBLIC_GUIDANCE,
        )
        stale_trigger = ConcernReferralTrigger.objects.create(
            concern=concern,
            key="obsolete-trigger",
            trigger_text="obsolete trigger",
            severity=TriggerSeverity.URGENT,
        )

        counts = seed_skin_concerns()

        stale_concern.refresh_from_db()
        stale_alias.refresh_from_db()
        stale_rule.refresh_from_db()
        stale_evidence.refresh_from_db()
        stale_trigger.refresh_from_db()
        self.assertFalse(stale_concern.is_active)
        self.assertFalse(stale_alias.is_active)
        self.assertFalse(stale_rule.is_active)
        self.assertFalse(stale_evidence.is_active)
        self.assertFalse(stale_trigger.is_active)
        self.assertEqual(counts["concerns_deactivated"], 1)
        self.assertEqual(counts["aliases_deactivated"], 1)
        self.assertEqual(counts["rules_deactivated"], 1)
        self.assertEqual(counts["evidence_deactivated"], 1)
        self.assertEqual(counts["triggers_deactivated"], 1)
        self.assertEqual(ConcernSearchService().search("obsolete alias"), [])
        self.assertEqual(
            ConcernResolutionService().referral_triggers_for_text(
                "I saw an obsolete trigger"
            ),
            [],
        )


class SkinConcernApiTests(TestCase):
    def setUp(self):
        seed_skin_concerns()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username="morgan")
        self.profile = Profile.objects.create(user=self.user)
        self.skin_profile = SkinProfile.objects.create(
            profile=self.profile,
            is_current=True,
        )

    def test_grouped_common_concern_list_is_public(self):
        response = self.client.get(reverse("skin-concern-list"))

        self.assertEqual(response.status_code, 200)
        groups = response.data["groups"]  # pyright: ignore[reportAttributeAccessIssue]
        self.assertTrue(groups)
        self.assertTrue(
            any(
                concern["slug"] == "breakouts"
                for group in groups
                for concern in group["concerns"]
            )
        )

    def test_search_endpoint_returns_alias_matches(self):
        response = self.client.get(reverse("skin-concern-search"), {"q": "zits"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["slug"], "breakouts")  # pyright: ignore[reportAttributeAccessIssue]

    def test_profile_concern_endpoint_saves_normalized_selections(self):
        self.client.force_authenticate(user=self.user)  # pyright: ignore[reportAttributeAccessIssue]

        response = self.client.post(
            reverse(
                "skin-profile-concerns",
                kwargs={"skin_profile_id": self.skin_profile.id},
            ),
            {
                "concerns": ["eczema", "rash"],
                "source": "search_selected",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [
                item["concern"]["slug"]
                for item in response.data["concerns"]  # pyright: ignore[reportAttributeAccessIssue]
            ],
            ["eczema_like_patches", "rash_safety"],
        )
        self.assertEqual(
            response.data["policy"]["recommendation_policy"],  # pyright: ignore[reportAttributeAccessIssue]
            RecommendationPolicy.SUPPRESS,
        )

        get_response = self.client.get(
            reverse(
                "skin-profile-concerns",
                kwargs={"skin_profile_id": self.skin_profile.id},
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(len(get_response.data["concerns"]), 2)  # pyright: ignore[reportAttributeAccessIssue]
