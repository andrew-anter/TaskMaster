from django.urls import path
from .api import DetailUpdateDeleteTaskApiView, ListCreateApiView

urlpatterns = [
    path("", ListCreateApiView.as_view(), name="list-tasks-api"),
    path("<int:pk>", DetailUpdateDeleteTaskApiView.as_view(), name="task-detail-api"),
]
