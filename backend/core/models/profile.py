from django.conf import settings
from django.db import models


class ProfileVisibility(models.TextChoices):
    PRIVATE = "private", "Private"
    UNLISTED = "unlisted", "Unlisted"
    PUBLIC = "public", "Public"


class Profile(models.Model):
    """Profile aggregate root linked one-to-one with Django auth.User."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    handle = models.SlugField(max_length=64, unique=True, null=True, blank=True)
    display_name = models.CharField(max_length=128, blank=True)
    bio = models.TextField(blank=True)
    pronouns = models.CharField(max_length=64, blank=True)
    avatar_url = models.URLField(max_length=1024, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    locale = models.CharField(max_length=16, blank=True)
    visibility = models.CharField(
        max_length=16,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.PRIVATE,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    @property
    def current_skin_profile(self):
        return (
            self.skin_profiles.filter(is_current=True)
            .order_by("-captured_at", "-id")
            .first()
        )

    def __str__(self) -> str:
        return self.display_name or self.handle or self.user.get_username()
