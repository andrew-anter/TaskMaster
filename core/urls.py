from django.contrib import admin
from django.urls import path, include
from todo import views as todo_views

from django.conf import settings  # For static files in DEBUG
from django.conf.urls.static import static

urlpatterns = [
    path("", todo_views.task_list_view, name="task_list"),
    path("admin/", admin.site.urls),
    path("tasks/", include("todo.urls")),
    path("accounts/", include("accounts.urls")),
    path("allauth/", include("allauth.urls")),
    path("api-auth/", include("rest_framework.urls")),
    path("api/v1/tasks/", include("todo.api-urls")),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
