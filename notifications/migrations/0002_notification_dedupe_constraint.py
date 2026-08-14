from django.db import migrations, models
from django.db.models import Count, Q


def dedupe_notifications(apps, schema_editor):
    """Remove duplicate (recipient, dedupe_key) rows, keeping the oldest."""
    Notification = apps.get_model("notifications", "Notification")

    duplicate_groups = (
        Notification.objects.exclude(dedupe_key="")
        .values("recipient_id", "dedupe_key")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
    )

    for group in duplicate_groups:
        duplicates = Notification.objects.filter(
            recipient_id=group["recipient_id"],
            dedupe_key=group["dedupe_key"],
        ).order_by("id")
        keep = duplicates.first()
        if keep is not None:
            duplicates.exclude(pk=keep.pk).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(dedupe_notifications, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="notification",
            constraint=models.UniqueConstraint(
                fields=["recipient", "dedupe_key"],
                condition=~Q(dedupe_key=""),
                name="unique_notification_dedupe_key",
            ),
        ),
    ]
