from notifications.types import register_type

# Notification type keys for task reminders
TYPE_DUE_TODAY = "task_due_today"
TYPE_DUE_SOON = "task_due_soon"
TYPE_OVERDUE = "task_overdue"
TYPE_SCHEDULED_TODAY = "task_scheduled_today"

_REMINDER_TYPES: dict[str, tuple[str, str]] = {
    TYPE_DUE_TODAY: ("Due Today", "nf-md-clock_alert_outline"),
    TYPE_DUE_SOON: ("Due Soon", "nf-md-clock_alert"),
    TYPE_OVERDUE: ("Overdue", "nf-md-alert"),
    TYPE_SCHEDULED_TODAY: ("Scheduled Today", "nf-md-calendar_today"),
}


def register_reminder_types() -> None:
    """Register display metadata for all task-reminder notification types."""
    for key, (label, icon) in _REMINDER_TYPES.items():
        register_type(key=key, label=label, icon=icon)
