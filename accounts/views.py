from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_not_required
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import render
from django.urls import reverse

from .forms import CustomLoginForm


@login_not_required
def login_view(request) -> HttpResponse:
    if request.method == "POST":
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            response: HttpResponse = HttpResponse()
            response["HX-Location"] = reverse(viewname="task_list")
            return response
    else:
        form = CustomLoginForm()

    context = {
        "form": form,
        "page_title": "Log In to TaskMaster",
        "google_client_id": settings.GOOGLE_CLIENT_ID,
    }
    return render(request=request, template_name="accounts/login.html", context=context)


def logout_view(request) -> HttpResponse:
    if request.method == "POST":
        logout(request=request)

        response = HttpResponse()
        response["HX-Location"] = reverse("login")
        return response
    return HttpResponseNotAllowed("POST")
