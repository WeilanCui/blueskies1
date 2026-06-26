from django.db import models

from skinconcerns.models.choices import AliasType
from skinconcerns.normalization import normalize_search_text


class ConcernAlias(models.Model):
    """Searchable user language that resolves to a canonical concern."""

    concern = models.ForeignKey(
        "skinconcerns.SkinConcern",
        on_delete=models.CASCADE,
        related_name="aliases",
    )
    alias_text = models.CharField(max_length=256)
    normalized_alias = models.CharField(max_length=256, unique=True, editable=False)
    alias_type = models.CharField(
        max_length=32,
        choices=AliasType.choices,
        default=AliasType.CONSUMER,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["alias_text"]
        indexes = [
            models.Index(fields=["normalized_alias"]),
            models.Index(fields=["alias_type", "is_active"]),
        ]

    def save(self, *args, **kwargs):
        self.normalized_alias = normalize_search_text(self.alias_text)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.alias_text
