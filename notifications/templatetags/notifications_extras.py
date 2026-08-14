from django import template

from ..types import get_type

register = template.Library()


@register.filter
def notification_icon(notification_type: str) -> str:
    """Return the Nerd Font icon class for a notification type key."""
    return get_type(notification_type).icon


@register.filter
def notification_label(notification_type: str) -> str:
    """Return the human-readable label for a notification type key."""
    return get_type(notification_type).label
