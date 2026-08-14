from django.urls import path

from . import views

urlpatterns = [
    path("", views.notification_list_view, name="notification_list"),
    path("panel/", views.notifications_panel_view, name="notification_panel"),
    path("badge/", views.notification_badge_view, name="notification_badge"),
    path(
        "mark-all-read/",
        views.mark_all_notifications_read_view,
        name="notifications_mark_all_read",
    ),
    path(
        "mark-read/<int:notification_id>/",
        views.mark_notification_read_view,
        name="notification_mark_read",
    ),
]
