from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TasksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tasks"
    verbose_name = _("Tasks")

    def ready(self) -> None:
        from .models import Task
        from .reminder_types import register_reminder_types
        from notifications.signals import register_notification_cascade

        register_reminder_types()
        register_notification_cascade(Task)
