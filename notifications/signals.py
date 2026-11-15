from django.db.models.signals import post_delete, post_save

from .models import Notification
from .services import invalidate_unread_count_on_commit


def _invalidate_unread_count_on_save(sender, instance, **kwargs) -> None:
    invalidate_unread_count_on_commit(user_id=instance.recipient_id)


def _invalidate_unread_count_on_delete(sender, instance, **kwargs) -> None:
    invalidate_unread_count_on_commit(user_id=instance.recipient_id)


def _cascade_delete_notifications(sender, instance, **kwargs) -> None:
    from django.contrib.contenttypes.models import ContentType

    content_type = ContentType.objects.get_for_model(sender)
    related = Notification.objects.filter(
        target_content_type=content_type,
        target_object_id=instance.pk,
    )
    recipient_ids = set(related.values_list("recipient_id", flat=True))
    related.delete()
    for recipient_id in recipient_ids:
        invalidate_unread_count_on_commit(user_id=recipient_id)


def register_notification_cascade(model) -> None:
    """
    Cascade-delete notifications whose GenericForeignKey ``target`` points at
    instances of ``model``.

    GenericForeignKey does not support ``on_delete`` cascades, so each app
    that can be a notification target calls this from its ``AppConfig.ready()``.
    """
    post_delete.connect(_cascade_delete_notifications, sender=model, weak=False)


def register_notification_signals() -> None:
    """
    Connect the unread-count cache-invalidation receivers for ``Notification``.

    Every row-level create/update/delete of a ``Notification`` drops the
    recipient's cached unread count, so paths that bypass the write services
    (Django admin edits) cannot serve a stale badge. Rows written or removed in
    bulk never send row signals (``bulk_create``, ``_raw_delete``), so those
    paths invalidate explicitly in ``notifications.services`` and
    ``notifications.tasks``. The invalidation is deferred to commit (see
    ``invalidate_unread_count_on_commit``) so a concurrent badge poll cannot
    re-cache a pre-commit count.
    """
    post_save.connect(_invalidate_unread_count_on_save, sender=Notification, weak=False)
    post_delete.connect(
        _invalidate_unread_count_on_delete, sender=Notification, weak=False
    )
