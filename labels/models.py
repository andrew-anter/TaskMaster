from django.db import models
from colorfield.fields import ColorField


class Label(models.Model):
    name = models.CharField(max_length=50)
    color = ColorField(default="#FFFFFFF")
    tasks = models.ManyToManyField("tasks.Task", related_name="labels", blank=True)

    def __str__(self):
        return f"{self.name}"
