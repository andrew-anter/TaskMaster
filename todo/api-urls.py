from django.urls import path
from .api import DetailTaskAPI, ListTasksAPI

urlpatterns = [
    path("", ListTasksAPI.as_view(), name="list-tasks-api"),
    path("<int:pk>", DetailTaskAPI.as_view(), name="get-task-api"),
]
