from django.shortcuts import render
from django.contrib.auth.decorators import login_not_required
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import login, logout
from django.http import HttpResponseNotAllowed, HttpResponse
from .forms import CustomLoginForm


@login_not_required
def login_view(request):
    form = CustomLoginForm()

    if request.method == "POST":
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            response = HttpResponse()
            response["HX-Location"] = reverse("task_list")
            return response
            return redirect(reverse("task_list"))
    else:
        form = CustomLoginForm()

    context = {"form": form, "page_title": "Log In to TaskMaster"}
    return render(request=request, template_name="accounts/login.html", context=context)


def logout_view(request):
    if request.method == "POST":
        logout(request=request)

        response = HttpResponse()
        response["HX-Location"] = reverse("login")
        return response
    return HttpResponseNotAllowed("POST")
