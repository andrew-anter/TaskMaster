from django.shortcuts import render
from django.contrib.auth.decorators import login_not_required
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import login
from .forms import CustomLoginForm


@login_not_required
def login_view(request):
    form = CustomLoginForm()

    if request.method == "POST":
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Get the 'next' URL from POST data, then GET data, or default to task_list
            next_url = request.POST.get("next", request.GET.get("next"))
            if next_url:
                return redirect(next_url)
            else:
                return redirect(reverse("task_list"))
    else:
        form = CustomLoginForm()

    context = {"form": form, "page_title": "Log In to TaskMaster"}
    return render(request=request, template_name="accounts/login.html", context=context)
