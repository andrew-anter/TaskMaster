from __future__ import annotations

from dataclasses import dataclass

DEFAULT_NOTIFICATION_TYPE = "default"

DEFAULT_ICON = "nf-cod-bell"


@dataclass(frozen=True)
class NotificationType:
    """Display metadata for a notification ``type`` key."""

    key: str
    label: str
    icon: str = DEFAULT_ICON


_REGISTRY: dict[str, NotificationType] = {}


def register_type(*, key: str, label: str, icon: str = DEFAULT_ICON) -> None:
    """Register (or overwrite) display metadata for a notification type."""
    _REGISTRY[key] = NotificationType(key=key, label=label, icon=icon)


def get_type(key: str) -> NotificationType:
    """Return the registered type for ``key``, or a sensible default."""
    return _REGISTRY.get(key, NotificationType(key=key, label=key))
