from django.urls import path
from .api import ListTasksAPI

urlpatterns = [
    path("", ListTasksAPI.as_view(), name="list-tasks-api"),
]
