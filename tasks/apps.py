from django.apps import AppConfig


class TasksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tasks"

    def ready(self) -> None:
        from notifications.signals import register_notification_cascade

        from .models import Task
        from .reminder_types import register_reminder_types

        register_reminder_types()
        register_notification_cascade(Task)
