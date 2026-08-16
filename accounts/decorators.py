from functools import wraps
from typing import Any

from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse


def require_non_authenticated_user(view_func: Any):
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any):
        if request.user.is_authenticated:
            return redirect(reverse("home"))

        response = view_func(request, *args, **kwargs)
        return response

    return wrapper
