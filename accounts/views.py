from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_not_required  # type: ignore
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from .decorators import require_non_authenticated_user
from .forms import CustomLoginForm, CustomRegisterForm
from .lockout import clear_login_failures, is_login_locked, record_login_failure

LOCKOUT_ERROR_MESSAGE = (
    "Too many failed sign-in attempts. Please try again in a few minutes."
)


def _get_safe_next_url(request: HttpRequest) -> str:
    next_url = request.POST.get("next") or request.GET.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return reverse("home")


@require_http_methods(request_method_list=["GET"])
@login_not_required
def root_redirect_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse("home"))
    return HttpResponseRedirect(reverse("login"))


@require_http_methods(request_method_list=["GET", "POST"])
@login_not_required
@require_non_authenticated_user
def login_view(request: HttpRequest) -> HttpResponse:
    status = 200
    if request.method == "POST":
        username = request.POST.get("username", "")
        form = CustomLoginForm(request, data=request.POST)
        if is_login_locked(request=request, username=username):
            # The template reads form errors, which triggers validation; keep
            # only the lockout message so the response never reveals whether
            # the supplied credentials were correct.
            form.full_clean()
            form.non_field_errors().clear()
            form.add_error(None, LOCKOUT_ERROR_MESSAGE)
            status = 429
        elif form.is_valid():
            user = form.get_user()
            clear_login_failures(request=request, username=username)
            login(request, user)

            return HttpResponseRedirect(_get_safe_next_url(request))
        else:
            record_login_failure(request=request, username=username)
    else:
        form = CustomLoginForm()

    context = {
        "form": form,
        "page_title": "Log In to TaskMaster",
        "google_login_enabled": bool(settings.GOOGLE_CLIENT_ID),
    }
    return render(
        request=request,
        template_name="accounts/login.html",
        context=context,
        status=status,
    )


@require_http_methods(request_method_list=["GET", "POST"])
@login_not_required
@require_non_authenticated_user
def register_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(request)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")

            return HttpResponseRedirect(_get_safe_next_url(request))
    else:
        form = CustomRegisterForm()

    context = {
        "form": form,
        "page_title": "Create your account",
    }
    return render(
        request=request, template_name="accounts/register.html", context=context
    )


@require_http_methods(request_method_list=["POST"])
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request=request)

    response = HttpResponse()
    response["HX-Location"] = reverse("login")
    return response
