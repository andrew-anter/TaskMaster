from django.urls import path
from .views import (
    label_list_view,
    label_create_view,
    label_update_view,
    label_delete_view,
    inline_label_form_view,
    inline_label_create_view,
)

urlpatterns = [
    path("", label_list_view, name="label_list"),
    path("create/", label_create_view, name="label_create"),
    path("<int:pk>/update/", label_update_view, name="label_update"),
    path("<int:pk>/delete/", label_delete_view, name="label_delete"),
    path("inline-form/", inline_label_form_view, name="inline_label_form"),
    path("inline-create/", inline_label_create_view, name="inline_label_create"),
]
