from django.conf import settings
from django.db import models
from colorfield.fields import ColorField


class Label(models.Model):
    name = models.CharField(max_length=50)
    color = ColorField(default="#FFFFFF")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="labels"
    )

    def __str__(self):
        return f"{self.name}"
