from django.urls import path

from . import views
from .api import DetailUpdateDeleteTaskApiView, ListCreateApiView, ToggleStatusAPI

main_patterns = [
    path("home/", views.task_list_view, name="home"),
    path("all-tasks/", views.all_tasks_view, name="all_tasks"),
    path("add/", views.task_add_partial_view, name="task_add"),
    path("update/<int:task_id>/", views.task_update_view, name="task_update"),
    path(
        "update-status/<int:task_id>/",
        views.task_update_status_view,
        name="update_task_status",
    ),
    path("delete/<int:task_id>/", views.task_delete_view, name="task_delete"),
    path("label/<int:label_id>/", views.task_list_by_label_view, name="tasks_by_label"),
    path("labels/refresh/", views.refresh_task_labels_view, name="refresh_task_labels"),
]

api_version_prefix = "api/v1"
api_urlpatterns = [
    path(f"{api_version_prefix}/", ListCreateApiView.as_view(), name="list-tasks-api"),
    path(
        f"{api_version_prefix}/<int:pk>/",
        DetailUpdateDeleteTaskApiView.as_view(),
        name="task-detail-api",
    ),
    path(
        f"{api_version_prefix}/<int:pk>/toggle/",
        ToggleStatusAPI.as_view(),
        name="toggle-task-status-api",
    ),
]

urlpatterns = [
    *main_patterns,
    *api_urlpatterns,
]
