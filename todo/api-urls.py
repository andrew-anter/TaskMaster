from django.urls import path
from .api import ListTasks

urlpatterns = [
    path("", ListTasks.as_view(), name="list-tasks-api"),
]
