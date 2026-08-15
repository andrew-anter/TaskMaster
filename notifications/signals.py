from django.db.models.signals import post_delete

from .selectors import invalidate_unread_notifications_count


def _cascade_delete_notifications(sender, instance, **kwargs) -> None:
    from django.contrib.contenttypes.models import ContentType

    from .models import Notification

    content_type = ContentType.objects.get_for_model(sender)
    related = Notification.objects.filter(
        target_content_type=content_type,
        target_object_id=instance.pk,
    )
    recipient_ids = set(related.values_list("recipient_id", flat=True))
    related.delete()
    for recipient_id in recipient_ids:
        invalidate_unread_notifications_count(user_id=recipient_id)


def register_notification_cascade(model) -> None:
    """
    Cascade-delete notifications whose GenericForeignKey ``target`` points at
    instances of ``model``.

    GenericForeignKey does not support ``on_delete`` cascades, so each app
    that can be a notification target calls this from its ``AppConfig.ready()``.
    """
    post_delete.connect(_cascade_delete_notifications, sender=model, weak=False)
