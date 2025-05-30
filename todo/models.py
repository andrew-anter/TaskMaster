from django.db import models


class TodoItem(models.Model):
    title = models.CharField(max_length=255)
    description = models.CharField(blank=True, default="")
    completed = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.title)

    class Meta:
        ordering = [
            "completed",
            "-created_at",
        ]
