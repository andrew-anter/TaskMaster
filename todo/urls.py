from django.urls import path
from . import views

urlpatterns = [
    path("", views.todo_list_view, name="todo_list"),
    path("add/", views.add_todo_view, name="add_todo"),
    path("toggle/<int:item_id>/", views.toggle_todo_view, name="toggle_todo"),
    path("delete/<int:item_id>/", views.delete_todo_view, name="delete_todo"),
]
