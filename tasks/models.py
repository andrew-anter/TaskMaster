from django.conf import settings
from django.db import models
from django.utils import timezone


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
    description = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TODO
    )
    priority = models.IntegerField(choices=Priority.choices, default=Priority.MEDIUM)
    due_datetime = models.DateTimeField(
        null=True, blank=True, verbose_name="Due date & time"
    )
    scheduled_date = models.DateField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    labels = models.ManyToManyField("labels.Label", related_name="tasks", blank=True)

    def __str__(self):
        return str(self.title)

    @property
    def is_overdue(self) -> bool:
        """True for incomplete tasks whose due date is in the past."""
        if not self.due_datetime or self.status == Task.Status.COMPLETED:
            return False
        return self.due_datetime < timezone.now()

    class Meta:
        ordering = ["status", "priority", "due_datetime"]
        verbose_name = "To-Do Item"
        verbose_name_plural = "To-Do Items"
