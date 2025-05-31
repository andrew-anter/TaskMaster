from django.urls import path
from . import views

urlpatterns = [
    path("", views.task_list_view, name="task_list"),
    path("add/", views.task_add_view, name="task_add"),
    path(
        "complete/<int:item_id>/",
        views.task_mark_as_completed_view,
        name="task_mark_as_completed",
    ),
    path(
        "update-status/<int:task_id>/",
        views.task_update_status_view,
        name="update_task_status",
    ),
    path("delete/<int:item_id>/", views.task_delete_view, name="task_delete"),
]
