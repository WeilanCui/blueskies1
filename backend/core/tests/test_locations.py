from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Location, Profile, ProfileLocation, WeatherSnapshot


class ProfileLocationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(  # pyright: ignore[reportAttributeAccessIssue]
            username="location-user",
            email="location@example.com",
            password="strong-test-pass-123",
        )
        self.other_user = get_user_model().objects.create_user(  # pyright: ignore[reportAttributeAccessIssue]
            username="other-location-user",
            email="other-location@example.com",
            password="strong-test-pass-123",
        )
        self.profile = Profile.objects.create(user=self.user)
        self.other_profile = Profile.objects.create(user=self.other_user)
        self.client.force_authenticate(user=self.user)

    def test_location_save_runs_model_validation(self):
        with self.assertRaises(ValidationError):
            Location.objects.create(country="US")

        self.assertEqual(Location.objects.count(), 0)

    def test_long_place_grid_key_is_bounded(self):
        location = Location.objects.create(
            city="A" * 128,
            region="B" * 128,
            country="US",
            precision="city",
        )

        self.assertLessEqual(len(location.grid_key), 160)
        self.assertTrue(location.grid_key.startswith("place:us:"))

    def test_long_place_grid_key_keeps_hash_suffix_for_uniqueness(self):
        first = Location.objects.create(
            city=("Shared Prefix " * 10)[:127] + "A",
            region=("Very Long Region " * 8)[:128],
            country="US",
            precision="city",
        )
        second = Location.objects.create(
            city=("Shared Prefix " * 10)[:127] + "B",
            region=("Very Long Region " * 8)[:128],
            country="US",
            precision="city",
        )

        self.assertLessEqual(len(first.grid_key), 160)
        self.assertLessEqual(len(second.grid_key), 160)
        self.assertNotEqual(first.grid_key, second.grid_key)

    def test_create_profile_location_normalizes_shared_location_and_sets_default(self):
        response = self.client.post(
            reverse("profile-location-list"),
            {
                "label": "Home",
                "postal_code": "10001",
                "city": "New York",
                "region": "NY",
                "country": "us",
                "precision": "postal_code",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Location.objects.count(), 1)
        location = Location.objects.get()
        self.assertEqual(location.grid_key, "postal:us:10001")
        self.assertEqual(location.country, "US")
        profile_location = ProfileLocation.objects.get(profile=self.profile)
        self.assertTrue(profile_location.is_default)
        self.assertEqual(profile_location.location, location)
        self.assertEqual(response.data["location"]["grid_key"], "postal:us:10001")  # pyright: ignore[reportAttributeAccessIssue]

    def test_multiple_profiles_reuse_same_shared_location_cache_bucket(self):
        shared_location = Location.objects.create(
            postal_code="10001",
            city="New York",
            region="NY",
            country="US",
            precision="postal_code",
        )
        ProfileLocation.objects.create(
            profile=self.other_profile,
            location=shared_location,
            label="Home",
            is_default=True,
        )

        response = self.client.post(
            reverse("profile-location-list"),
            {
                "label": "Apartment",
                "postal_code": "10001",
                "city": "New York",
                "region": "NY",
                "country": "US",
                "precision": "postal_code",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Location.objects.count(), 1)
        self.assertEqual(ProfileLocation.objects.get(profile=self.profile).location, shared_location)

    def test_current_context_returns_cached_weather_snapshot(self):
        location = Location.objects.create(
            postal_code="10001",
            city="New York",
            region="NY",
            country="US",
            latitude=Decimal("40.7128"),
            longitude=Decimal("-74.0060"),
            precision="postal_code",
        )
        ProfileLocation.objects.create(
            profile=self.profile,
            location=location,
            label="Home",
            is_default=True,
        )
        WeatherSnapshot.objects.create(
            location=location,
            observed_at=timezone.make_aware(datetime(2026, 6, 14, 12, 0)),
            expires_at=timezone.now() + timezone.timedelta(hours=1),  # pyright: ignore[reportAttributeAccessIssue]
            uv_index=Decimal("8.0"),
            uv_max=Decimal("8.0"),
            raw_payload={"UV_INDEX": "8"},
        )

        with patch("core.services.weather.requests.get") as mock_get:
            response = self.client.get(reverse("profile-location-current-context"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["profile_location"]["label"], "Home")  # pyright: ignore[reportAttributeAccessIssue]
        self.assertEqual(response.data["weather_snapshot"]["uv_index"], "8.0")  # pyright: ignore[reportAttributeAccessIssue]
        mock_get.assert_not_called()

    @patch("core.services.weather.requests.get")
    def test_refresh_weather_fetches_epa_uv_and_caches_snapshot(self, mock_get):
        location = Location.objects.create(
            postal_code="10001",
            city="New York",
            region="NY",
            country="US",
            precision="postal_code",
        )
        profile_location = ProfileLocation.objects.create(
            profile=self.profile,
            location=location,
            label="Home",
            is_default=True,
        )
        epa_response = Mock()
        epa_response.json.return_value = [
            {"UV_INDEX": "5", "DATE": "2026-06-14"},
            {"UV_INDEX": "8", "DATE": "2026-06-15"},
        ]
        epa_response.raise_for_status.return_value = None
        weather_response = Mock()
        weather_response.json.return_value = {
            "current": {
                "time": "2026-06-15T12:00",
                "temperature_2m": 27.4,
                "relative_humidity_2m": 63,
                "cloud_cover": 42,
            }
        }
        weather_response.raise_for_status.return_value = None
        mock_get.side_effect = [epa_response, weather_response]

        response = self.client.post(
            reverse("profile-location-refresh-weather", args=[profile_location.id]),  # pyright: ignore[reportAttributeAccessIssue]
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(WeatherSnapshot.objects.count(), 1)
        snapshot = WeatherSnapshot.objects.get()
        self.assertEqual(snapshot.location, location)
        self.assertEqual(snapshot.uv_index, Decimal("8.0"))
        self.assertEqual(snapshot.temperature_c, Decimal("27.4"))
        self.assertEqual(snapshot.humidity_percent, 63)
        self.assertEqual(snapshot.cloud_cover_percent, 42)
        self.assertEqual(response.data["weather_snapshot"]["uv_index"], "8.0")  # pyright: ignore[reportAttributeAccessIssue]
        self.assertEqual(response.data["weather_snapshot"]["humidity_percent"], 63)  # pyright: ignore[reportAttributeAccessIssue]
        self.assertIn("/getEnvirofactsUVDAILY/ZIP/10001/JSON", mock_get.call_args.args[0])
        self.assertIn("current=temperature_2m", mock_get.call_args_list[1].args[0])

    def test_refresh_weather_rejects_location_without_weather_sharing(self):
        location = Location.objects.create(
            postal_code="10001",
            city="New York",
            region="NY",
            country="US",
            precision="postal_code",
        )
        profile_location = ProfileLocation.objects.create(
            profile=self.profile,
            location=location,
            label="Home",
            is_default=True,
            share_weather_context=False,
        )

        response = self.client.post(
            reverse("profile-location-refresh-weather", args=[profile_location.id]),  # pyright: ignore[reportAttributeAccessIssue]
            format="json",
        )

        self.assertEqual(response.status_code, 400)
