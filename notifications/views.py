from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from common.http import hx_location_response, is_partial_request

from .models import Notification
from .selectors import (
    get_notifications_for_user,
    get_unread_notifications_count,
)
from .services import mark_all_notifications_read, mark_notification_read

PANEL_LIMIT = 10

PANEL_TEMPLATE = "notifications/partials/_notification_panel.html"
BADGE_TEMPLATE = "notifications/partials/_notification_badge.html"
REFRESH_TEMPLATE = "notifications/partials/_notification_refresh.html"
ITEM_TEMPLATE = "notifications/partials/_notification_item.html"
LIST_TEMPLATE = "notifications/notification_list.html"
LIST_PARTIAL_TEMPLATE = "notifications/partials/_notification_list.html"


@require_http_methods(["GET"])
def notification_list_view(request):
    """Full-page list of all notifications for the current user."""
    notifications = get_notifications_for_user(user=request.user)
    unread_count = get_unread_notifications_count(user=request.user)

    context = {
        "notifications": notifications,
        "unread_count": unread_count,
        "page_title": "Notifications",
    }
    if is_partial_request(request):
        return render(request, LIST_PARTIAL_TEMPLATE, context)
    return render(request, LIST_TEMPLATE, context)


@require_http_methods(["GET"])
def notifications_panel_view(request):
    """Renders the bell dropdown panel (latest notifications + actions)."""
    notifications = get_notifications_for_user(user=request.user, limit=PANEL_LIMIT)
    unread_count = get_unread_notifications_count(user=request.user)
    context = {
        "notifications": notifications,
        "unread_count": unread_count,
    }
    return render(request, PANEL_TEMPLATE, context)


@require_http_methods(["GET"])
def notification_badge_view(request):
    """Renders just the unread-count badge, for HTMX polling."""
    context = {"unread_count": get_unread_notifications_count(user=request.user)}
    response = render(request, BADGE_TEMPLATE, context)
    response["HX-Trigger"] = "refresh-notification-panel"
    return response


@require_http_methods(["POST"])
def mark_all_notifications_read_view(request):
    """Marks every notification read and refreshes the requesting UI."""
    mark_all_notifications_read(recipient=request.user)

    if request.POST.get("source") == "page":
        context = {
            "notifications": get_notifications_for_user(user=request.user),
            "unread_count": 0,
            "page_title": "Notifications",
        }
        return render(request, LIST_PARTIAL_TEMPLATE, context)

    notifications = get_notifications_for_user(user=request.user, limit=PANEL_LIMIT)
    context = {
        "notifications": notifications,
        "unread_count": 0,
    }
    return render(request, REFRESH_TEMPLATE, context)


@require_http_methods(["POST"])
def mark_notification_read_view(request, notification_id):
    """Marks one notification read and navigates to its destination link."""
    try:
        notification = mark_notification_read(
            recipient=request.user, notification_id=notification_id
        )
    except Notification.DoesNotExist:
        raise Http404("Notification not found")
    destination = notification.link
    if not destination or not url_has_allowed_host_and_scheme(
        destination,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        destination = reverse("notification_list")
    return hx_location_response(destination)
