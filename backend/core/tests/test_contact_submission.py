from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from core.models import ContactSubmission, ContactSubmissionStatus


class ContactSubmissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_anonymous_contact_submit_creates_submission_without_user(self):
        response = self.client.post(
            reverse("contact-submit"),
            {
                "name": "  Jordan Lee  ",
                "email": "  jordan@example.com  ",
                "feedback": "  I want early access to the regimen tracker.  ",
            },
            format="json",
            HTTP_USER_AGENT="Test Browser",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(ContactSubmission.objects.count(), 1)
        submission = ContactSubmission.objects.get()
        self.assertEqual(submission.name, "Jordan Lee")
        self.assertEqual(submission.email, "jordan@example.com")
        self.assertEqual(submission.feedback, "I want early access to the regimen tracker.")
        self.assertIsNone(submission.user)
        self.assertEqual(submission.status, ContactSubmissionStatus.NEW)
        self.assertEqual(submission.source, "landing_page")
        self.assertEqual(submission.user_agent, "Test Browser")
        self.assertEqual(
            response.data["detail"],  # pyright: ignore[reportAttributeAccessIssue]
            "Thanks for reaching out. We will reach out shortly.",
        )

    def test_authenticated_contact_submit_attaches_current_user(self):
        user = get_user_model().objects.create_user(  # pyright: ignore[reportAttributeAccessIssue]
            username="jordan",
            email="jordan@example.com",
            password="test-pass",
        )
        self.client.force_authenticate(user=user)  # pyright: ignore[reportAttributeAccessIssue]

        response = self.client.post(
            reverse("contact-submit"),
            {
                "name": "Jordan Lee",
                "email": "jordan@example.com",
                "feedback": "I want early access to the regimen tracker.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        submission = ContactSubmission.objects.get()
        self.assertEqual(submission.user, user)

    def test_contact_submit_ignores_payload_provided_user(self):
        user_model = get_user_model()
        current_user = user_model.objects.create_user(  # pyright: ignore[reportAttributeAccessIssue]
            username="current",
            email="current@example.com",
            password="test-pass",
        )
        other_user = user_model.objects.create_user(  # pyright: ignore[reportAttributeAccessIssue]
            username="other",
            email="other@example.com",
            password="test-pass",
        )
        self.client.force_authenticate(user=current_user)  # pyright: ignore[reportAttributeAccessIssue]

        response = self.client.post(
            reverse("contact-submit"),
            {
                "name": "Jordan Lee",
                "email": "jordan@example.com",
                "feedback": "I want early access to the regimen tracker.",
                "user": other_user.id,
                "user_id": other_user.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        submission = ContactSubmission.objects.get()
        self.assertEqual(submission.user, current_user)

    def test_anonymous_contact_submit_ignores_payload_provided_user(self):
        other_user = get_user_model().objects.create_user(  # pyright: ignore[reportAttributeAccessIssue]
            username="other",
            email="other@example.com",
            password="test-pass",
        )

        response = self.client.post(
            reverse("contact-submit"),
            {
                "name": "Jordan Lee",
                "email": "jordan@example.com",
                "feedback": "I want early access to the regimen tracker.",
                "user": other_user.id,
                "user_id": other_user.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        submission = ContactSubmission.objects.get()
        self.assertIsNone(submission.user)

    def test_contact_submit_requires_name(self):
        response = self.client.post(
            reverse("contact-submit"),
            {
                "name": "   ",
                "email": "jordan@example.com",
                "feedback": "Hello",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ContactSubmission.objects.count(), 0)

    def test_contact_submit_requires_valid_email(self):
        response = self.client.post(
            reverse("contact-submit"),
            {
                "name": "Jordan Lee",
                "email": "not-an-email",
                "feedback": "Hello",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ContactSubmission.objects.count(), 0)

    def test_contact_submit_requires_email(self):
        response = self.client.post(
            reverse("contact-submit"),
            {
                "name": "Jordan Lee",
                "email": "",
                "feedback": "Hello",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ContactSubmission.objects.count(), 0)

    def test_contact_submit_requires_feedback(self):
        response = self.client.post(
            reverse("contact-submit"),
            {
                "name": "Jordan Lee",
                "email": "jordan@example.com",
                "feedback": "   ",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ContactSubmission.objects.count(), 0)
