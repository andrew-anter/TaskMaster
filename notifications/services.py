from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.db.models import Model

from .models import Notification

if TYPE_CHECKING:
    from accounts.models import User


def _resolve_target(
    target: Model | None,
) -> tuple[ContentType | None, int | None]:
    if target is None:
        return None, None
    content_type = ContentType.objects.get_for_model(target)
    return content_type, int(target.pk)  # type: ignore[attr-defined]


def _validate_entry(entry: dict) -> None:
    """Validate the keys of a ``notify_many`` entry dict."""
    allowed = {"recipient", "type", "message", "link", "actor", "target", "dedupe_key"}
    unknown = set(entry) - allowed
    if unknown:
        raise ValueError(f"Unknown notification entry key(s): {sorted(unknown)}")
    missing = {"recipient", "type", "message"} - set(entry)
    if missing:
        raise ValueError(f"Missing notification entry key(s): {sorted(missing)}")


def _base_notification(
    *,
    recipient: User,
    type: str,
    message: str,
    link: str,
    actor: User | None,
    target: Model | None,
) -> Notification:
    content_type, object_id = _resolve_target(target)
    return Notification(
        recipient=recipient,
        type=type,
        message=message,
        link=link,
        actor=actor,
        target_content_type=content_type,
        target_object_id=object_id,
    )


@transaction.atomic
def notify(
    *,
    recipient: User,
    type: str,
    message: str,
    link: str = "",
    actor: User | None = None,
    target: Model | None = None,
    dedupe_key: str = "",
) -> Notification | None:
    """
    Create a notification for a single recipient.

    When ``dedupe_key`` is provided, this is idempotent: if a notification
    with the same ``recipient`` and ``dedupe_key`` already exists, no new row
    is created and ``None`` is returned. The ``(recipient, dedupe_key)`` pair
    is enforced unique at the database level, so a concurrent duplicate insert
    is also suppressed.

    Returns:
        The created Notification, or None if deduplicated.
    """
    if (
        dedupe_key
        and Notification.objects.filter(
            recipient=recipient, dedupe_key=dedupe_key
        ).exists()
    ):
        return None
    notification = _base_notification(
        recipient=recipient,
        type=type,
        message=message,
        link=link,
        actor=actor,
        target=target,
    )
    notification.dedupe_key = dedupe_key
    try:
        with transaction.atomic():
            notification.save()
    except IntegrityError:
        # Lost a race against a concurrent insert with the same dedupe_key.
        return None
    return notification


@transaction.atomic
def notify_bulk(
    *,
    recipients: Iterable[User],
    type: str,
    message: str,
    link: str = "",
    actor: User | None = None,
    target: Model | None = None,
    dedupe_keys: Iterable[str] | None = None,
) -> int:
    """
    Create the same notification for many recipients in a single bulk insert.

    ``recipients`` may be a QuerySet or an iterable of User instances.
    If ``dedupe_keys`` is provided it must be the same length as
    ``recipients`` and gives each notification an idempotency key.

    Returns:
        The number of notifications created.
    """
    recipients = list(recipients)
    if not recipients:
        return 0

    dedupe_keys = list(dedupe_keys) if dedupe_keys is not None else []
    if dedupe_keys and len(dedupe_keys) != len(recipients):
        raise ValueError("dedupe_keys must match the number of recipients")

    entries = [
        {
            "recipient": recipient,
            "type": type,
            "message": message,
            "link": link,
            "actor": actor,
            "target": target,
            "dedupe_key": dedupe_keys[index] if dedupe_keys else "",
        }
        for index, recipient in enumerate(recipients)
    ]
    return notify_many(entries=entries)


@transaction.atomic
def notify_many(*, entries: Iterable[dict]) -> int:
    """
    Bulk-create heterogeneous notifications in a single insert.

    Each entry is a dict with the same keys as :func:`notify` (``recipient``,
    ``type``, ``message`` and the optional ``link``, ``actor``, ``target``,
    ``dedupe_key``). Unknown or missing keys raise ``ValueError``. Entries
    whose ``dedupe_key`` already exists for their recipient are skipped. Rows
    are inserted with ``ON CONFLICT DO NOTHING`` semantics, so concurrent
    duplicates cannot raise.

    Returns:
        The number of notifications created.
    """
    entry_list = [dict(entry) for entry in entries]
    if not entry_list:
        return 0

    for entry in entry_list:
        _validate_entry(entry)

    existing_pairs: set[tuple[int, str]] = set()
    keyed_entries = [
        (index, entry)
        for index, entry in enumerate(entry_list)
        if entry.get("dedupe_key")
    ]
    if keyed_entries:
        pairs = Notification.objects.filter(
            recipient__in=[
                entry_list[index]["recipient"] for index, _ in keyed_entries
            ],
            dedupe_key__in=[entry["dedupe_key"] for _, entry in keyed_entries],
        ).values_list("recipient_id", "dedupe_key")
        existing_pairs = {(recipient_id, key) for recipient_id, key in pairs}

    notifications: list[Notification] = []
    for index, entry in enumerate(entry_list):
        key = entry.get("dedupe_key", "")
        recipient = entry["recipient"]
        if key and (recipient.pk, key) in existing_pairs:
            continue
        notification = _base_notification(
            recipient=recipient,
            type=entry["type"],
            message=entry["message"],
            link=entry.get("link", ""),
            actor=entry.get("actor"),
            target=entry.get("target"),
        )
        notification.dedupe_key = key
        notifications.append(notification)

    created = Notification.objects.bulk_create(notifications, ignore_conflicts=True)
    return created.__len__()


@transaction.atomic
def mark_notification_read(*, recipient: User, notification_id: int) -> Notification:
    """Mark a single notification as read (owner-only)."""
    notification = Notification.objects.get(pk=notification_id, recipient=recipient)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return notification


@transaction.atomic
def mark_all_notifications_read(*, recipient: User) -> int:
    """Mark every notification for ``recipient`` as read; returns rows updated."""
    return Notification.objects.filter(recipient=recipient, is_read=False).update(
        is_read=True
    )
