from django.apps import apps
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from accounts.views import root_redirect_view

optional_apps = {
    "accounts": "accounts/",
    "tasks": "tasks/",
    "labels": "labels/",
    "notifications": "notifications/",
}

urlpatterns = [
    path("", root_redirect_view, name="root_redirect"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("allauth/", include("allauth.urls")),
    path("api-auth/", include("rest_framework.urls")),
]

for app_name, app_url_prefix in optional_apps.items():
    if apps.is_installed(app_name):
        urlpatterns.append(path(app_url_prefix, include(f"{app_name}.urls")))

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
