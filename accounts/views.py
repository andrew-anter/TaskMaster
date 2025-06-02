from django.shortcuts import render
from django.contrib.auth.decorators import login_not_required
from .forms import CustomLoginForm


@login_not_required
def login_view(request):
    form = CustomLoginForm()
    return render(
        request=request, template_name="accounts/login.html", context={"form": form}
    )
