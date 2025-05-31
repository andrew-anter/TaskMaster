from django.urls import path
from . import views

urlpatterns = [
    path("", views.task_list_view, name="task_list"),
    path("tasks", views.task_list_partial_view, name="task-list-partial"),
    path("add/", views.task_add_partial_view, name="task_add"),
    path(
        "update-status/<int:task_id>/",
        views.task_update_status_view,
        name="update_task_status",
    ),
    path("delete/<int:item_id>/", views.task_delete_view, name="task_delete"),
]
