from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications"

    def ready(self) -> None:
        from .signals import register_notification_signals
        from .types import register_type

        register_notification_signals()
        register_type(
            key="system_announcement",
            label="Announcement",
            icon="nf-md-bullhorn",
        )
