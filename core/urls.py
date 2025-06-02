from django.contrib import admin
from django.urls import path, include
# from django.shortcuts import redirect

from django.conf import settings  # For static files in DEBUG
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("tasks/", include("todo.urls")),
    path("accounts/", include("accounts.urls")),
    # path("", lambda _: redirect("task_list", permanent=False)),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
