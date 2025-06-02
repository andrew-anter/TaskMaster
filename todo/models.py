from django.db import models
from accounts.models import User


class Task(models.Model):
    class Priority(models.IntegerChoices):
        LOW = 3, "Low"
        MEDIUM = 2, "Medium"
        HIGH = 1, "High"
        NONE = 0, "None"

    class Status(models.TextChoices):
        TODO = "TODO", "To Do"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        ON_HOLD = "ON_HOLD", "On Hold"
        COMPLETED = "COMPLETED", "Completed"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TODO
    )
    priority = models.IntegerField(choices=Priority.choices, default=Priority.MEDIUM)
    due_date = models.DateTimeField(
        null=True,
        blank=True,
    )
    scheduled_date = models.DateField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.title)

    class Meta:
        ordering = ["status", "priority", "due_date"]
        verbose_name = "To-Do Item"
        verbose_name_plural = "To-Do Items"
