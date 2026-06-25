from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    DailyCheckIn,
    DailyProductUse,
    Formulation,
    Product,
    Profile,
    ReactionEvent,
    Routine,
    RoutineItem,
)


class RoutineApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(  # pyright: ignore[reportAttributeAccessIssue]
            username="routine-user",
            email="routine@example.com",
            password="strong-test-pass-123",
        )
        self.other_user = get_user_model().objects.create_user(  # pyright: ignore[reportAttributeAccessIssue]
            username="other-user",
            email="other@example.com",
            password="strong-test-pass-123",
        )
        self.profile = Profile.objects.create(user=self.user)
        self.other_profile = Profile.objects.create(user=self.other_user)
        self.product = Product.objects.create(name="Ultra Facial Cream")
        self.formulation = Formulation.objects.create(product=self.product)
        self.client.force_authenticate(user=self.user)

    def test_routine_create_preserves_order_and_product_formulation_links(self):
        response = self.client.post(
            reverse("routine-list"),
            {
                "name": "AM Routine",
                "time_of_day": "am",
                "items": [
                    {
                        "position": 1,
                        "routine_step": "cleanser",
                        "raw_product_name": "Manual Cleanser",
                    },
                    {
                        "position": 2,
                        "routine_step": "moisturizer",
                        "product_id": self.product.id,  # pyright: ignore[reportAttributeAccessIssue]
                        "formulation_id": self.formulation.id,  # pyright: ignore[reportAttributeAccessIssue]
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        routine = Routine.objects.get(profile=self.profile)
        self.assertEqual(list(routine.items.values_list("position", flat=True)), [1, 2])  # pyright: ignore[reportAttributeAccessIssue]
        linked_item = routine.items.get(position=2)  # pyright: ignore[reportAttributeAccessIssue]
        self.assertEqual(linked_item.product, self.product)
        self.assertEqual(linked_item.formulation, self.formulation)
        self.assertEqual(response.data["items"][0]["display_name"], "Manual Cleanser")  # pyright: ignore[reportAttributeAccessIssue]

    def test_routine_update_reorders_items_and_preserves_item_ids(self):
        routine = Routine.objects.create(
            profile=self.profile,
            name="AM Routine",
            time_of_day="am",
        )
        first = RoutineItem.objects.create(
            routine=routine,
            position=1,
            routine_step="cleanser",
            raw_product_name="Gentle Cleanser",
        )
        second = RoutineItem.objects.create(
            routine=routine,
            position=2,
            routine_step="moisturizer",
            product=self.product,
            formulation=self.formulation,
        )

        response = self.client.put(
            reverse("routine-detail", kwargs={"pk": routine.pk}),
            {
                "name": routine.name,
                "time_of_day": routine.time_of_day,
                "is_active": True,
                "items": [
                    {
                        "id": second.id,  # pyright: ignore[reportAttributeAccessIssue]
                        "position": 1,
                        "routine_step": second.routine_step,
                        "product_id": self.product.id,  # pyright: ignore[reportAttributeAccessIssue]
                        "formulation_id": self.formulation.id,  # pyright: ignore[reportAttributeAccessIssue]
                        "raw_product_name": "",
                    },
                    {
                        "id": first.id,  # pyright: ignore[reportAttributeAccessIssue]
                        "position": 2,
                        "routine_step": first.routine_step,
                        "raw_product_name": first.raw_product_name,
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(routine.items.order_by("position").values_list("id", flat=True)),  # pyright: ignore[reportAttributeAccessIssue]
            [second.id, first.id],  # pyright: ignore[reportAttributeAccessIssue]
        )
        self.assertEqual(
            list(routine.items.order_by("position").values_list("position", flat=True)),  # pyright: ignore[reportAttributeAccessIssue]
            [1, 2],
        )
        self.assertEqual(
            [item["id"] for item in response.data["items"]],  # pyright: ignore[reportAttributeAccessIssue]
            [second.id, first.id],  # pyright: ignore[reportAttributeAccessIssue]
        )

    def test_activating_same_timing_deactivates_prior_routine_in_domain_logic(self):
        existing = Routine.objects.create(
            profile=self.profile,
            name="Old AM",
            time_of_day="am",
            is_active=True,
        )

        response = self.client.post(
            reverse("routine-list"),
            {"name": "New AM", "time_of_day": "am", "is_active": True},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        existing.refresh_from_db()
        self.assertFalse(existing.is_active)
        self.assertTrue(Routine.objects.get(name="New AM").is_active)

    def test_user_only_sees_own_routines(self):
        Routine.objects.create(profile=self.profile, name="Mine", time_of_day="am")
        Routine.objects.create(profile=self.other_profile, name="Theirs", time_of_day="am")

        response = self.client.get(reverse("routine-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([routine["name"] for routine in response.data], ["Mine"])  # pyright: ignore[reportAttributeAccessIssue]

    def test_add_product_creates_active_routine_when_missing(self):
        response = self.client.post(
            reverse("routine-add-product"),
            {
                "time_of_day": "am",
                "product_id": self.product.id,  # pyright: ignore[reportAttributeAccessIssue]
                "formulation_id": self.formulation.id,  # pyright: ignore[reportAttributeAccessIssue]
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        routine = Routine.objects.get(profile=self.profile, time_of_day="am")
        item = routine.items.get()  # pyright: ignore[reportAttributeAccessIssue]
        self.assertEqual(routine.name, "AM Routine")
        self.assertEqual(item.position, 1)
        self.assertEqual(item.product, self.product)
        self.assertEqual(item.formulation, self.formulation)
        self.assertEqual(item.routine_step, "treatment")
        self.assertTrue(response.data["created"])  # pyright: ignore[reportAttributeAccessIssue]

    def test_add_product_appends_to_existing_routine(self):
        routine = Routine.objects.create(
            profile=self.profile,
            name="PM Routine",
            time_of_day="pm",
        )
        RoutineItem.objects.create(
            routine=routine,
            position=1,
            raw_product_name="Manual cleanser",
        )

        response = self.client.post(
            reverse("routine-add-product"),
            {
                "routine_id": routine.id,  # pyright: ignore[reportAttributeAccessIssue]
                "product_id": self.product.id,  # pyright: ignore[reportAttributeAccessIssue]
                "routine_step": "moisturizer",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        item = routine.items.get(position=2)  # pyright: ignore[reportAttributeAccessIssue]
        self.assertEqual(item.product, self.product)
        self.assertEqual(item.routine_step, "moisturizer")
        self.assertEqual(response.data["routine"]["id"], routine.id)  # pyright: ignore[reportAttributeAccessIssue]

    def test_add_product_to_routine_is_idempotent_for_same_product(self):
        routine = Routine.objects.create(
            profile=self.profile,
            name="AM Routine",
            time_of_day="am",
        )
        existing_item = RoutineItem.objects.create(
            routine=routine,
            position=1,
            product=self.product,
        )

        response = self.client.post(
            reverse("routine-add-product"),
            {
                "routine_id": routine.id,  # pyright: ignore[reportAttributeAccessIssue]
                "product_id": self.product.id,  # pyright: ignore[reportAttributeAccessIssue]
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["created"])  # pyright: ignore[reportAttributeAccessIssue]
        self.assertEqual(response.data["item_id"], existing_item.id)  # pyright: ignore[reportAttributeAccessIssue]
        self.assertEqual(routine.items.count(), 1)  # pyright: ignore[reportAttributeAccessIssue]

    def test_add_product_rejects_other_users_routine(self):
        other_routine = Routine.objects.create(
            profile=self.other_profile,
            name="Other PM",
            time_of_day="pm",
        )

        response = self.client.post(
            reverse("routine-add-product"),
            {
                "routine_id": other_routine.id,  # pyright: ignore[reportAttributeAccessIssue]
                "product_id": self.product.id,  # pyright: ignore[reportAttributeAccessIssue]
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_add_product_acquires_profile_row_lock(self):
        """Verify that save() acquires a row-level lock on the profile."""
        with mock.patch.object(
            Profile.objects, "select_for_update", wraps=Profile.objects.select_for_update
        ) as spy:
            response = self.client.post(
                reverse("routine-add-product"),
                {
                    "time_of_day": "am",
                    "product_id": self.product.id,
                },
                format="json",
            )

            self.assertEqual(response.status_code, 201)
            spy.assert_called_once()
            # Verify the returned routine was created as expected
            routine = Routine.objects.get(profile=self.profile, time_of_day="am")
            self.assertEqual(routine.items.count(), 1)

    def test_today_log_creates_checkin_and_daily_product_uses(self):
        routine = Routine.objects.create(profile=self.profile, name="PM", time_of_day="pm")
        item = RoutineItem.objects.create(
            routine=routine,
            position=1,
            routine_step="treatment",
            product=self.product,
            formulation=self.formulation,
        )

        response = self.client.post(
            reverse("daily-checkin-today"),
            {
                "skin_feel": "good",
                "skin_notes": "Less redness.",
                "completed_routine_item_ids": [item.id],  # pyright: ignore[reportAttributeAccessIssue]
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        checkin = DailyCheckIn.objects.get(
            profile=self.profile,
            checkin_date=timezone.localdate(),
        )
        self.assertEqual(checkin.skin_feel, "good")
        product_use = DailyProductUse.objects.get(checkin=checkin)
        self.assertEqual(product_use.routine_item, item)
        self.assertEqual(product_use.product, self.product)
        self.assertEqual(response.data["completed_routine_item_ids"], [item.id])  # pyright: ignore[reportAttributeAccessIssue]

    def test_today_log_rejects_other_users_routine_item(self):
        other_routine = Routine.objects.create(
            profile=self.other_profile,
            name="Other PM",
            time_of_day="pm",
        )
        other_item = RoutineItem.objects.create(
            routine=other_routine,
            position=1,
            raw_product_name="Other product",
        )

        response = self.client.post(
            reverse("daily-checkin-today"),
            {"completed_routine_item_ids": [other_item.id]},  # pyright: ignore[reportAttributeAccessIssue]
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_reaction_event_links_to_routine_context(self):
        routine = Routine.objects.create(profile=self.profile, name="PM", time_of_day="pm")
        item = RoutineItem.objects.create(
            routine=routine,
            position=1,
            raw_product_name="Retinol",
        )

        response = self.client.post(
            reverse("reaction-list"),
            {
                "title": "Mild peeling",
                "severity": "mild",
                "status": "active",
                "routine": routine.id,  # pyright: ignore[reportAttributeAccessIssue]
                "routine_item": item.id,  # pyright: ignore[reportAttributeAccessIssue]
                "product_id": self.product.id,  # pyright: ignore[reportAttributeAccessIssue]
                "symptoms": ["peeling", "peeling"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        reaction = ReactionEvent.objects.get(profile=self.profile)
        self.assertEqual(reaction.routine, routine)
        self.assertEqual(reaction.routine_item, item)
        self.assertEqual(reaction.product, self.product)
        self.assertEqual(reaction.symptoms, ["peeling"])

    def test_reaction_patch_preserves_existing_context_fields(self):
        reaction = ReactionEvent.objects.create(
            profile=self.profile,
            title="Mild peeling",
            severity="mild",
            status="active",
            product=self.product,
            formulation=self.formulation,
            suspected_trigger="Retinol",
            symptoms=["peeling"],
            notes="Started yesterday.",
        )

        response = self.client.patch(
            reverse("reaction-detail", args=[reaction.id]),  # pyright: ignore[reportAttributeAccessIssue]
            {"status": "resolved"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        reaction.refresh_from_db()
        self.assertEqual(reaction.status, "resolved")
        self.assertEqual(reaction.product, self.product)
        self.assertEqual(reaction.formulation, self.formulation)
        self.assertEqual(reaction.suspected_trigger, "Retinol")
        self.assertEqual(reaction.symptoms, ["peeling"])
        self.assertEqual(reaction.notes, "Started yesterday.")

    def test_routine_create_rejects_unknown_product_id(self):
        response = self.client.post(
            reverse("routine-list"),
            {
                "name": "AM Routine",
                "time_of_day": "am",
                "items": [
                    {
                        "position": 1,
                        "routine_step": "cleanser",
                        "product_id": 99999,
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Product not found.", str(response.content))

    def test_routine_create_rejects_unknown_formulation_id(self):
        response = self.client.post(
            reverse("routine-list"),
            {
                "name": "AM Routine",
                "time_of_day": "am",
                "items": [
                    {
                        "position": 1,
                        "routine_step": "cleanser",
                        "formulation_id": 99999,
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Formulation not found.", str(response.content))

    def test_routine_create_rejects_formulation_from_different_product(self):
        other_product = Product.objects.create(name="Other Product")
        other_formulation = Formulation.objects.create(product=other_product)

        response = self.client.post(
            reverse("routine-list"),
            {
                "name": "AM Routine",
                "time_of_day": "am",
                "items": [
                    {
                        "position": 1,
                        "routine_step": "cleanser",
                        "product_id": self.product.id,
                        "formulation_id": other_formulation.id,
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Formulation must belong to product.", str(response.content))

    def test_routine_create_rejects_missing_product_formulation_and_raw_name(self):
        response = self.client.post(
            reverse("routine-list"),
            {
                "name": "AM Routine",
                "time_of_day": "am",
                "items": [
                    {
                        "position": 1,
                        "routine_step": "cleanser",
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Routine item needs a product, formulation, or raw_product_name.", str(response.content))

    def test_add_product_rejects_unknown_product_id(self):
        response = self.client.post(
            reverse("routine-add-product"),
            {
                "time_of_day": "am",
                "product_id": 99999,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Product not found.", str(response.content))

    def test_add_product_rejects_unknown_formulation_id(self):
        response = self.client.post(
            reverse("routine-add-product"),
            {
                "time_of_day": "am",
                "formulation_id": 99999,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Formulation not found.", str(response.content))

    def test_add_product_rejects_formulation_from_different_product(self):
        other_product = Product.objects.create(name="Other Product")
        other_formulation = Formulation.objects.create(product=other_product)

        response = self.client.post(
            reverse("routine-add-product"),
            {
                "time_of_day": "am",
                "product_id": self.product.id,
                "formulation_id": other_formulation.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Formulation must belong to product.", str(response.content))

    def test_add_product_rejects_missing_product_formulation_and_raw_name(self):
        response = self.client.post(
            reverse("routine-add-product"),
            {
                "time_of_day": "am",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Routine item needs a product, formulation, or raw_product_name.", str(response.content))
