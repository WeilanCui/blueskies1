from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import ContactSubmission, ContactSubmissionStatus
from core.services.contact_verification import digest_contact_verification_code


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

    @patch("core.views.create_contact_verification_code", return_value="123456")
    @patch("core.views.send_contact_verification_code")
    def test_contact_request_code_sends_email_and_creates_pending_submission(
        self,
        send_verification_code,
        create_code,
    ):
        response = self.client.post(
            reverse("contact-request-code"),
            {
                "email": "  Jordan@Example.com  ",
            },
            format="json",
            HTTP_USER_AGENT="Test Browser",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["detail"],  # pyright: ignore[reportAttributeAccessIssue]
            "Check your email for a six-digit verification code.",
        )
        self.assertIs(response.data["alreadyVerified"], False)  # pyright: ignore[reportAttributeAccessIssue]
        create_code.assert_called_once_with()
        send_verification_code.assert_called_once_with("jordan@example.com", "123456")

        submission = ContactSubmission.objects.get()
        self.assertEqual(submission.email, "jordan@example.com")
        self.assertEqual(submission.name, "Private beta signup")
        self.assertEqual(submission.feedback, "Joined the private beta waitlist.")
        self.assertEqual(submission.source, "private_beta")
        self.assertEqual(submission.user_agent, "Test Browser")
        self.assertEqual(
            submission.verification_code_digest,
            digest_contact_verification_code("jordan@example.com", "123456"),
        )
        self.assertNotEqual(submission.verification_code_digest, "123456")
        self.assertIsNotNone(submission.verification_code_expires_at)
        self.assertIsNotNone(submission.verification_code_last_sent_at)
        self.assertIsNone(submission.email_verified_at)

    @patch("core.views.create_contact_verification_code", return_value="123456")
    @patch("core.views.send_contact_verification_code")
    def test_contact_verify_code_marks_submission_verified(
        self,
        send_verification_code,
        create_code,
    ):
        self.client.post(
            reverse("contact-request-code"),
            {
                "email": "jordan@example.com",
            },
            format="json",
        )

        response = self.client.post(
            reverse("contact-verify-code"),
            {"email": "Jordan@Example.com", "code": "123456"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["detail"],  # pyright: ignore[reportAttributeAccessIssue]
            "You're verified and on the Blueskies early access list.",
        )
        submission = ContactSubmission.objects.get()
        self.assertIsNotNone(submission.email_verified_at)
        self.assertEqual(submission.verification_attempts, 0)
        self.assertEqual(submission.verification_code_digest, "")
        self.assertIsNone(submission.verification_code_expires_at)
        send_verification_code.assert_called_once_with("jordan@example.com", "123456")
        create_code.assert_called_once_with()

    def test_contact_verify_code_rejects_wrong_code_and_counts_attempts(self):
        now = timezone.now()
        ContactSubmission.objects.create(
            name="Jordan Lee",
            email="jordan@example.com",
            feedback="I want early access.",
            verification_code_digest=digest_contact_verification_code(
                "jordan@example.com",
                "123456",
            ),
            verification_code_expires_at=now + timedelta(minutes=10),
            verification_code_last_sent_at=now,
        )

        response = self.client.post(
            reverse("contact-verify-code"),
            {"email": "jordan@example.com", "code": "000000"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],  # pyright: ignore[reportAttributeAccessIssue]
            "That code is not correct.",
        )
        self.assertEqual(ContactSubmission.objects.get().verification_attempts, 1)

    @patch("core.views.send_contact_verification_code")
    def test_contact_request_code_enforces_resend_cooldown(self, send_verification_code):
        now = timezone.now()
        ContactSubmission.objects.create(
            name="Jordan Lee",
            email="jordan@example.com",
            feedback="I want early access.",
            verification_code_digest=digest_contact_verification_code(
                "jordan@example.com",
                "123456",
            ),
            verification_code_expires_at=now + timedelta(minutes=10),
            verification_code_last_sent_at=now,
        )

        response = self.client.post(
            reverse("contact-request-code"),
            {
                "email": "jordan@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],  # pyright: ignore[reportAttributeAccessIssue]
            "Please wait a minute before requesting another code.",
        )
        send_verification_code.assert_not_called()

    @patch("core.views.create_contact_verification_code", return_value="123456")
    @patch(
        "core.views.send_contact_verification_code",
        side_effect=ImproperlyConfigured("Email verification is not configured."),
    )
    def test_contact_request_code_reports_missing_mailgun_config(
        self,
        send_verification_code,
        create_code,
    ):
        response = self.client.post(
            reverse("contact-request-code"),
            {
                "email": "jordan@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],  # pyright: ignore[reportAttributeAccessIssue]
            "Email verification is not configured.",
        )
        self.assertEqual(ContactSubmission.objects.count(), 0)
        create_code.assert_called_once_with()
        send_verification_code.assert_called_once_with("jordan@example.com", "123456")
