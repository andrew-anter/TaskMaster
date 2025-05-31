from django.urls import path
from . import views

urlpatterns = [
    path("", views.todo_list_view, name="todo_list"),
    path("add/", views.add_todo_view, name="add_todo"),
    path(
        "complete/<int:item_id>/",
        views.mark_item_as_completed,
        name="mark_item_as_completed",
    ),
    path("delete/<int:item_id>/", views.delete_todo_view, name="delete_todo"),
]
