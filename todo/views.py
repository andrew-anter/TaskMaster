from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import (
    HttpResponse,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from todo.exceptions import DueDateInPastError, ScheduledDateInPastError

from .forms import TaskForm
from .models import Task
from .selectors import (
    get_all_tasks_for_user,
    get_task_for_user,
    get_today_tasks_for_user,
    get_upcoming_tasks_for_user,
)
from .services import (
    task_add_service,
    task_delete_service,
    task_update_service,
    toggle_task_status_service,
)
import logging

logger = logging.getLogger(__name__)
ADD_TASK_TEMPLATE_NAME = "todo/partials/_add_task.html"


@require_http_methods(["GET"])
def task_list_view(request):
    today_tasks = get_today_tasks_for_user(user=request.user)
    upcoming_tasks = get_upcoming_tasks_for_user(user=request.user)

    context = {
        "today_tasks": today_tasks,
        "upcoming_tasks": upcoming_tasks,
        "page_title": "My Tasks",
        "Status": Task.Status,
        "Priority": Task.Priority,
    }
    return render(request, "todo/task_list.html", context)


@require_http_methods(["GET"])
def task_list_partial_view(request):
    today_tasks = get_today_tasks_for_user(user=request.user)
    upcoming_tasks = get_upcoming_tasks_for_user(user=request.user)

    context = {
        "today_tasks": today_tasks,
        "upcoming_tasks": upcoming_tasks,
        "page_title": "My Tasks",
        "Status": Task.Status,
        "Priority": Task.Priority,
    }
    return render(request, "todo/partials/_task_list.html", context)


@require_http_methods(request_method_list=["GET", "POST"])
def task_add_partial_view(request):
    template_name = ADD_TASK_TEMPLATE_NAME
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            try:
                task_add_service(
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
                return render(request, template_name, context)

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
                return render(request, template_name, context)

    else:
        form = TaskForm()

    context = {"form": form, "page_title": "Add New Task"}
    return render(request, template_name, context)


@require_http_methods(request_method_list=["POST"])
def task_update_status_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)
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


def handle_valid_update_form(request, task_id, form):
    page_title = "Update Task"
    try:
        _, success = task_update_service(
            user=request.user,
            task_id=task_id,
            title=form.cleaned_data["title"],
            description=form.cleaned_data.get("description"),
            status=form.cleaned_data["status"],
            priority=form.cleaned_data["priority"],
            due_datetime=form.cleaned_data.get("due_datetime"),
            scheduled_date=form.cleaned_data.get("scheduled_date"),
        )
        if success:
            messages.success(request, "Task have been updated successfully.")

        else:
            messages.warning(
                request,
                "Task update failed. Maybe all the task attributes are still the same",
            )
        response = HttpResponse()
        response["HX-Location"] = reverse("task_list")
        return response

    except Task.DoesNotExist:
        response = HttpResponse()
        response["HX-Location"] = reverse("task_list")
        messages.error(request, "No task assiociated with this id.")
        return response

    except DueDateInPastError as e:
        form.add_error("due_datetime", f"{e}")
        page_title = "Update Task (Errors)"

    except ScheduledDateInPastError as e:
        form.add_error("scheduled_date", f"{e}")
        page_title = "Update Task (Errors)"

    except Exception as e:
        logger.error(f"An excpetion occurred in task_update_view: {e}")

    context = {
        "form": form,
        "task_id": task_id,
        "page_title": page_title,
    }
    return render(request, template_name=ADD_TASK_TEMPLATE_NAME, context=context)


@require_http_methods(request_method_list=["GET", "POST"])
def task_update_view(request, task_id):
    task = get_task_for_user(user=request.user, task_id=task_id)

    if not task:
        response = HttpResponse()
        response["HX-Location"] = reverse("task_list")
        messages.error(request, "No task assiociated with this id.")
        return response

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            return handle_valid_update_form(request, task_id, form)

    form = TaskForm(instance=task)
    page_title = "Update Task"
    context = {
        "form": form,
        "task_id": task_id,
        "page_title": page_title,
    }
    return render(request, template_name=ADD_TASK_TEMPLATE_NAME, context=context)


@require_http_methods(request_method_list=["POST"])
def task_delete_view(request, task_id):
    deleted = task_delete_service(user=request.user, task_id=task_id)
    if deleted:
        messages.success(request, message="Task deleted successfully.")
    else:
        messages.warning(
            request, message="An error occurred, no changes have been made"
        )

    response = HttpResponse()
    response["HX-Location"] = reverse("task_list")
    return response


@require_http_methods(request_method_list=["GET"])
def all_tasks_view(request):
    tasks = get_all_tasks_for_user(user=request.user)

    context = {
        "all_tasks": tasks,
        "page_title": "All Tasks",
        "Status": Task.Status,
        "Priority": Task.Priority,
    }
    return render(
        request=request,
        template_name="todo/partials/_all_tasks_list.html",
        context=context,
    )
