from django.urls import path
from .api import DetailUpdateDeleteTaskApiView, ListCreateApiView, ToggleStatusAPI

urlpatterns = [
    path("", ListCreateApiView.as_view(), name="list-tasks-api"),
    path("<int:pk>", DetailUpdateDeleteTaskApiView.as_view(), name="task-detail-api"),
    path("<int:pk>/toggle/", ToggleStatusAPI.as_view(), name="toggle-task-status-api"),
]
