from .selectors import get_unread_notifications_count


def unread_notifications_count(request):
    """
    Expose the authenticated user's unread notification count to all templates
    as ``unread_count`` (used by the navbar bell badge).
    """
    if request.user.is_authenticated:
        return {"unread_count": get_unread_notifications_count(user=request.user)}
    return {}
