from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_not_required  # type: ignore
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import CustomLoginForm, CustomRegisterForm


@require_http_methods(request_method_list=["GET"])
@login_not_required
def root_redirect_view(request) -> HttpResponse:
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse("home"))
    return HttpResponseRedirect(reverse("login"))


@require_http_methods(request_method_list=["GET", "POST"])
@login_not_required
def login_view(request) -> HttpResponse:
    if request.method == "POST":
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            return HttpResponseRedirect(reverse("home"))
    else:
        form = CustomLoginForm()

    context = {
        "form": form,
        "page_title": "Log In to TaskMaster",
        "google_client_id": settings.GOOGLE_CLIENT_ID,
    }
    return render(request=request, template_name="accounts/login.html", context=context)


@require_http_methods(request_method_list=["GET", "POST"])
@login_not_required
def register_view(request) -> HttpResponse:
    if request.method == "POST":
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(request)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")

            return HttpResponseRedirect(reverse("home"))
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
def logout_view(request) -> HttpResponse:
    logout(request=request)

    response = HttpResponse()
    response["HX-Location"] = reverse("login")
    return response
