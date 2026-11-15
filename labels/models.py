from typing import ClassVar

from colorfield.fields import ColorField
from django.conf import settings
from django.db import models


class Label(models.Model):
    name = models.CharField(max_length=50)
    color = ColorField(default="#FFFFFF")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="labels"
    )

    class Meta:
        constraints: ClassVar[list] = [
            # Case-sensitive DB backstop for the service's case-insensitive check.
            models.UniqueConstraint(
                fields=["owner", "name"], name="unique_label_per_owner"
            ),
        ]

    def __str__(self):
        return f"{self.name}"
