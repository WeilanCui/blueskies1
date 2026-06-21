import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from core.models import Profile, ProfileConstraint, SkinProfile


class AuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_signup_creates_user_profile_and_session(self):
        response = self.client.post(
            reverse("auth-signup"),
            {
                "email": "alex@example.com",
                "password": "strong-test-pass-123",
                "display_name": "Alex",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        user = get_user_model().objects.get(email="alex@example.com")
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertEqual(response.data["user"]["email"], "alex@example.com")

        me = self.client.get(reverse("auth-me"))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["user"]["id"], user.id)

    def test_signup_rejects_duplicate_email(self):
        get_user_model().objects.create_user(
            username="alex",
            email="alex@example.com",
            password="strong-test-pass-123",
        )

        response = self.client.post(
            reverse("auth-signup"),
            {"email": "ALEX@example.com", "password": "strong-test-pass-123"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_login_accepts_email_and_logout_clears_session(self):
        user = get_user_model().objects.create_user(
            username="alex",
            email="alex@example.com",
            password="strong-test-pass-123",
        )
        Profile.objects.create(user=user)

        response = self.client.post(
            reverse("auth-login"),
            {"identifier": "alex@example.com", "password": "strong-test-pass-123"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["id"], user.id)

        self.assertEqual(self.client.get(reverse("auth-me")).status_code, 200)
        self.assertEqual(self.client.post(reverse("auth-logout")).status_code, 200)
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, 401)

    def test_login_rejects_invalid_credentials(self):
        response = self.client.post(
            reverse("auth-login"),
            {"identifier": "missing@example.com", "password": "wrong-pass"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_me_patch_updates_display_name(self):
        user = get_user_model().objects.create_user(
            username="display-user",
            email="display-user@example.com",
            password="strong-test-pass-123",
        )
        Profile.objects.create(user=user, display_name="Old Name")
        self.client.force_authenticate(user=user)

        response = self.client.patch(
            reverse("auth-me"),
            {"display_name": "New Name"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["display_name"], "New Name")
        self.assertEqual(
            self.client.get(reverse("auth-me")).data["user"]["display_name"],
            "New Name",
        )

    def test_me_patch_requires_authentication(self):
        response = self.client.patch(
            reverse("auth-me"),
            {"display_name": "New Name"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_me_patch_rejects_long_display_name(self):
        user = get_user_model().objects.create_user(
            username="long-name-user",
            email="long-name-user@example.com",
            password="strong-test-pass-123",
        )
        Profile.objects.create(user=user, display_name="Old Name")
        self.client.force_authenticate(user=user)

        response = self.client.patch(
            reverse("auth-me"),
            {"display_name": "N" * 129},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Profile.objects.get(user=user).display_name, "Old Name")

    def test_login_sets_csrf_cookie_for_session_authenticated_writes(self):
        user = get_user_model().objects.create_user(
            username="csrf-user",
            email="csrf-user@example.com",
            password="strong-test-pass-123",
        )
        Profile.objects.create(user=user)
        client = Client(enforce_csrf_checks=True, HTTP_HOST="localhost")

        login = client.post(
            reverse("auth-login"),
            data=json.dumps(
                {
                    "identifier": "csrf-user@example.com",
                    "password": "strong-test-pass-123",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(login.status_code, 200)
        self.assertIn("csrftoken", client.cookies)
        csrf_token = client.cookies["csrftoken"].value

        response = client.post(
            reverse("intake"),
            data=json.dumps({"skin_type": "combination"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 201)


class IntakeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="morgan",
            email="morgan@example.com",
            password="strong-test-pass-123",
        )

    def test_intake_requires_authentication(self):
        response = self.client.get(reverse("intake"))

        self.assertEqual(response.status_code, 403)

    def test_intake_updates_current_skin_profile_and_constraints(self):
        self.client.force_authenticate(user=self.user)
        profile = Profile.objects.create(user=self.user)
        skin_profile = SkinProfile.objects.create(
            profile=profile,
            skin_type="dry",
            is_current=True,
        )

        response = self.client.post(
            reverse("intake"),
            {
                "skin_type": "combination",
                "skin_types": ["combination", "oily", "combination"],
                "fitzpatrick_skin_type": "type_iii",
                "baseline_sensitivity": 6,
                "primary_concerns": ["acne", "redness", "acne"],
                "goals": ["fewer breakouts"],
                "goals_text": "stronger barrier",
                "pregnancy_status": "not_provided",
                "climate": "humid",
                "routine_notes": "Using a gentle cleanser.",
                "sensitivities": ["Fragrance", "Retinoids", "Fragrance"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(profile.skin_profiles.count(), 1)

        current = profile.skin_profiles.get(is_current=True)
        self.assertEqual(current.id, skin_profile.id)
        self.assertEqual(current.skin_type, "combination")
        self.assertEqual(current.skin_types, ["combination", "oily"])
        self.assertEqual(current.fitzpatrick_skin_type, "type_iii")
        self.assertEqual(current.baseline_sensitivity, 6)
        self.assertEqual(current.primary_concerns, ["acne", "redness"])
        self.assertEqual(current.goals, ["fewer breakouts", "stronger barrier"])
        self.assertEqual(current.climate, "humid")

        constraints = ProfileConstraint.objects.filter(profile=profile, source="intake")
        self.assertEqual(constraints.count(), 2)
        self.assertEqual(
            sorted(constraint.raw_label for constraint in constraints),
            ["Fragrance", "Retinoids"],
        )
        self.assertEqual(response.data["skin_profile"]["id"], current.id)
        self.assertEqual(
            response.data["skin_profile"]["skin_types"],
            ["combination", "oily"],
        )
        self.assertEqual(response.data["sensitivities"], ["Fragrance", "Retinoids"])

    def test_intake_post_creates_skin_profile_when_none_exists(self):
        self.client.force_authenticate(user=self.user)
        profile = Profile.objects.create(user=self.user)

        response = self.client.post(
            reverse("intake"),
            {"skin_type": "combination"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(profile.skin_profiles.count(), 1)
        self.assertEqual(
            profile.skin_profiles.get(is_current=True).skin_type,
            "combination",
        )
        self.assertEqual(
            profile.skin_profiles.get(is_current=True).skin_types,
            ["combination"],
        )

    def test_intake_accepts_multiple_skin_types_without_single_skin_type(self):
        self.client.force_authenticate(user=self.user)
        profile = Profile.objects.create(user=self.user)

        response = self.client.post(
            reverse("intake"),
            {"skin_types": ["oily", "sensitive"]},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        skin_profile = profile.skin_profiles.get(is_current=True)
        self.assertEqual(skin_profile.skin_type, "oily")
        self.assertEqual(skin_profile.skin_types, ["oily", "sensitive"])
        self.assertEqual(response.data["skin_profile"]["skin_type"], "oily")
        self.assertEqual(
            response.data["skin_profile"]["skin_types"],
            ["oily", "sensitive"],
        )

    def test_intake_put_updates_current_skin_profile(self):
        self.client.force_authenticate(user=self.user)
        profile = Profile.objects.create(user=self.user)
        skin_profile = SkinProfile.objects.create(
            profile=profile,
            skin_type="dry",
            primary_concerns=["flaking"],
            is_current=True,
        )

        response = self.client.put(
            reverse("intake"),
            {
                "skin_type": "oily",
                "primary_concerns": ["shine", "pores"],
                "sensitivities": ["Fragrance"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(profile.skin_profiles.count(), 1)
        skin_profile.refresh_from_db()
        self.assertTrue(skin_profile.is_current)
        self.assertEqual(skin_profile.skin_type, "oily")
        self.assertEqual(skin_profile.primary_concerns, ["shine", "pores"])
        self.assertEqual(response.data["skin_profile"]["id"], skin_profile.id)
        self.assertEqual(response.data["sensitivities"], ["Fragrance"])

    def test_intake_get_returns_existing_profile_state(self):
        self.client.force_authenticate(user=self.user)
        profile = Profile.objects.create(user=self.user)
        SkinProfile.objects.create(
            profile=profile,
            skin_type="oily",
            primary_concerns=["oiliness"],
            goals=["less shine"],
            is_current=True,
        )
        ProfileConstraint.objects.create(
            profile=profile,
            raw_label="Fragrance",
            source="intake",
        )

        response = self.client.get(reverse("intake"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["skin_profile"]["skin_type"], "oily")
        self.assertEqual(response.data["sensitivities"], ["Fragrance"])


class ProtectedWriteEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_formulation_submit_requires_authentication(self):
        response = self.client.post(
            reverse("formulation-submit"),
            {
                "name": "Example Product",
                "formulation": "Water, Glycerin",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
