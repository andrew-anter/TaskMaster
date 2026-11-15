from django.apps import apps
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_not_required  # type: ignore
from django.urls import include, path
from django.views.generic import RedirectView

from accounts.views import root_redirect_view

# Anonymous users must reach these, so exempt them from LoginRequiredMiddleware.
_allauth_login_redirect = login_not_required(
    RedirectView.as_view(pattern_name="login", permanent=False)
)
_allauth_signup_redirect = login_not_required(
    RedirectView.as_view(pattern_name="register", permanent=False)
)

optional_apps = {
    "accounts": "accounts/",
    "tasks": "tasks/",
    "labels": "labels/",
    "notifications": "notifications/",
}

urlpatterns = [
    path("", root_redirect_view, name="root_redirect"),
    path("admin/", admin.site.urls),
    # allauth ships usable /allauth/login/ and /allauth/signup/ pages that
    # bypass accounts/views.py; forward them to the canonical styled views.
    # Password reset and social auth stay on allauth.
    path("allauth/login/", _allauth_login_redirect),
    path("allauth/signup/", _allauth_signup_redirect),
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
