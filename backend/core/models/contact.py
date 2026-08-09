from django.conf import settings
from django.db import models


class ContactSubmissionStatus(models.TextChoices):
    NEW = "new", "New"
    REVIEWED = "reviewed", "Reviewed"
    CONTACTED = "contacted", "Contacted"
    ARCHIVED = "archived", "Archived"


class ContactSubmission(models.Model):
    """A landing-page contact or feedback submission."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_submissions",
    )
    name = models.CharField(max_length=128)
    email = models.EmailField()
    feedback = models.TextField()
    status = models.CharField(
        max_length=16,
        choices=ContactSubmissionStatus.choices,
        default=ContactSubmissionStatus.NEW,
    )
    source = models.CharField(max_length=64, default="landing_page")
    user_agent = models.TextField(blank=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    verification_code_digest = models.CharField(max_length=64, blank=True)
    verification_code_expires_at = models.DateTimeField(null=True, blank=True)
    verification_code_last_sent_at = models.DateTimeField(null=True, blank=True)
    verification_attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["email"]),
            models.Index(fields=["email_verified_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"
