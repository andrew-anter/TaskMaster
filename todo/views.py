from django.contrib import messages
from django.http import (
    HttpResponse,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from todo.exceptions import DueDateInPastError

from .forms import TaskForm
from .models import Task
from .selectors import (
    get_all_tasks,
    get_task_for_user,
    get_today_tasks,
    get_upcoming_tasks,
)
from .services import add_task_service, toggle_task_status_service


def task_list_view(request):
    today_tasks = get_today_tasks(user=request.user)
    upcoming_tasks = get_upcoming_tasks(user=request.user)

    context = {
        "today_tasks": today_tasks,
        "upcoming_tasks": upcoming_tasks,
        "page_title": "My Tasks",
        "Status": Task.Status,
        "Priority": Task.Priority,
    }
    return render(request, "todo/task_list.html", context)


def task_list_partial_view(request):
    today_tasks = get_today_tasks(user=request.user)
    upcoming_tasks = get_upcoming_tasks(user=request.user)

    context = {
        "today_tasks": today_tasks,
        "upcoming_tasks": upcoming_tasks,
        "page_title": "My Tasks",
        "Status": Task.Status,
        "Priority": Task.Priority,
    }
    return render(request, "todo/partials/_task_list.html", context)


def task_add_partial_view(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            try:
                add_task_service(
                    title=form.cleaned_data["title"],
                    description=form.cleaned_data.get("description"),
                    status=form.cleaned_data["status"],
                    priority=form.cleaned_data["priority"],
                    due_datetime=form.cleaned_data.get("due_datetime"),
                    scheduled_date=form.cleaned_data.get("scheduled_date"),
                    owner=request.user,
                )
            except DueDateInPastError as e:
                form.add_error(None, f"{e}")
                context = {"form": form, "page_title": "Add New Task (Errors)"}
                return render(request, "todo/partials/_add_task.html", context)

            if request.htmx:
                response = HttpResponse()  # Empty response is fine
                response["HX-Location"] = reverse("task_list")
                messages.success(request, "Task added successfully")
                return response
            else:
                messages.success(request, "Task added successfully!")
                return HttpResponseRedirect(reverse("task_list"))
        else:  # Form is invalid
            if request.htmx:
                context = {"form": form, "page_title": "Add New Task (Errors)"}
                return render(request, "todo/partials/_add_task.html", context)

    else:
        form = TaskForm()

    context = {"form": form, "page_title": "Add New Task"}
    return render(request, "todo/partials/_add_task.html", context)


def task_update_status_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.method == "POST":
        toggle_task_status_service(task=task)

        if request.htmx:
            context = {
                "task": task,
                "Status": Task.Status,
                "Priority": Task.Priority,
            }
            return render(request, "todo/partials/_task_list_item.html", context)
        else:
            # Fallback for non-HTMX requests (though this view is primarily for HTMX now)
            messages.info(request, f"Task '{task.title}' status updated.")
            return HttpResponseRedirect(reverse("task_list"))

    # GET requests to this URL are not typical for this action, redirect or show error
    return redirect(reverse("task_list"))


def task_update_view(request, task_id):
    task = get_task_for_user(user=request.user, task_id=task_id)

    if request.method == "POST":
        pass

    if not task:
        response = HttpResponse()  # Empty response is fine
        response["HX-Location"] = reverse("task_list")
        messages.error(request, "No task assiociated with this id.")
        return response

    form = TaskForm(instance=task)
    context = {"form": form, "page_title": "Update Task"}
    return render(request, "todo/partials/_add_task.html", context)


def task_delete_view(request, item_id):
    item = get_object_or_404(Task, id=item_id)
    if request.method == "POST":
        item_title = item.title
        item.delete()
        messages.warning(request, f"Task '{item_title}' deleted.")
        return HttpResponseRedirect(reverse("task_list"))
    return HttpResponseRedirect(reverse("task_list"))


def all_tasks_view(request):
    tasks = get_all_tasks(user=request.user)

    context = {
        "all_tasks": tasks,
        "page_title": "All Tasks",
        "Status": Task.Status,
        "Priority": Task.Priority,
    }
    return render(request, "todo/partials/_all_tasks_list.html", context)
