from datetime import date

from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.http import (
    HttpResponseRedirect,
    Http404,
)
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from common.http import hx_location_response

from .exceptions import DueDateInPastError, ScheduledDateInPastError

from .forms import TaskForm
from .models import Task
from .selectors import (
    get_task_for_user,
    get_tasks_by_label,
    get_today_tasks_for_user,
    get_upcoming_tasks_for_user,
    search_tasks_for_user,
)
from .services import (
    task_add_service,
    task_delete_service,
    task_update_service,
    toggle_task_status_service,
)
from labels.models import Label
import logging

logger = logging.getLogger(__name__)
ADD_TASK_TEMPLATE_NAME = "todo/partials/_add_task.html"
TASKS_PER_PAGE = 25


def parse_date_param(value: str | None) -> date | None:
    """Parses an ISO date query param, returning None for empty/invalid values."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def parse_status_param(value: str | None) -> str | None:
    """Validates a status query param against Task.Status values."""
    if not value:
        return None
    value = value.upper()
    return value if value in Task.Status.values else None


def parse_priority_param(value: str | None) -> int | None:
    """Validates a priority query param against Task.Priority values."""
    if not value:
        return None
    try:
        priority = int(value)
    except (TypeError, ValueError):
        return None
    return priority if priority in Task.Priority.values else None


def parse_label_param(user, value: str | None) -> int | None:
    """Validates a label query param, ensuring it belongs to the user."""
    if not value:
        return None
    try:
        label_id = int(value)
    except (TypeError, ValueError):
        return None
    if not user.labels.filter(pk=label_id).exists():
        return None
    return label_id


def paginate_tasks(request, tasks, *, page_size: int = TASKS_PER_PAGE):
    """Paginates a queryset and builds prev/next page URLs preserving GET params."""
    paginator = Paginator(tasks, page_size)
    page_obj = paginator.get_page(request.GET.get("page"))

    def page_url(page_number: int) -> str | None:
        if page_number < 1 or page_number > paginator.num_pages:
            return None
        params = request.GET.copy()
        params["page"] = page_number
        return f"?{params.urlencode()}"

    return page_obj, page_url(page_obj.number - 1), page_url(page_obj.number + 1)


@require_http_methods(["GET"])
def task_list_view(request):
    today_tasks = get_today_tasks_for_user(user=request.user)
    upcoming_tasks = get_upcoming_tasks_for_user(user=request.user)

    today_page_obj, prev_page_url, next_page_url = paginate_tasks(request, today_tasks)

    context = {
        "today_tasks": today_page_obj.object_list,
        "upcoming_tasks": upcoming_tasks,
        "page_obj": today_page_obj,
        "prev_page_url": prev_page_url,
        "next_page_url": next_page_url,
        "page_base_url": reverse("home"),
        "page_title": "My Tasks",
        "Status": Task.Status,
        "Priority": Task.Priority,
    }
    if request.htmx and not request.htmx.boosted:
        return render(request, "todo/partials/_task_list.html", context)
    return render(request, "todo/task_list.html", context)


@require_http_methods(request_method_list=["GET", "POST"])
def task_add_partial_view(request):
    template_name = ADD_TASK_TEMPLATE_NAME
    if request.method == "POST":
        form = TaskForm(request.POST, user=request.user)
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
                    labels=form.cleaned_data.get("labels"),
                )
            except DueDateInPastError as e:
                form.add_error(None, f"{e}")
                context = {
                    "form": form,
                    "page_title": "Add New Task (Errors)",
                    "user_labels": Label.objects.filter(owner=request.user),
                    "selected_label_ids": [
                        lbl.pk for lbl in form.cleaned_data.get("labels", [])
                    ],
                }
                return render(request, template_name, context)

            if request.htmx:
                response = hx_location_response(reverse("home"))
                messages.success(request, "Task added successfully")
                return response
            else:
                messages.success(request, "Task added successfully!")
                return HttpResponseRedirect(reverse("home"))
        else:
            if request.htmx:
                context = {
                    "form": form,
                    "page_title": "Add New Task (Errors)",
                    "user_labels": Label.objects.filter(owner=request.user),
                    "selected_label_ids": [
                        lbl.pk for lbl in form.cleaned_data.get("labels", [])
                    ],
                }
                return render(request, template_name, context)

    else:
        form = TaskForm(user=request.user)

    context = {
        "form": form,
        "page_title": "Add New Task",
        "user_labels": Label.objects.filter(owner=request.user),
        "selected_label_ids": [],
    }
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
        return HttpResponseRedirect(reverse("all_tasks"))


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
            labels=form.cleaned_data.get("labels"),
        )
        if success:
            messages.success(request, "Task have been updated successfully.")

        else:
            messages.warning(
                request,
                "Task update failed. Maybe all the task attributes are still the same",
            )
        response = hx_location_response(reverse("home"))
        return response

    except Task.DoesNotExist:
        response = hx_location_response(reverse("home"))
        messages.error(request, "No task assiociated with this id.")
        return response

    except DueDateInPastError as e:
        form.add_error("due_datetime", f"{e}")
        page_title = "Update Task (Errors)"

    except ScheduledDateInPastError as e:
        form.add_error("scheduled_date", f"{e}")
        page_title = "Update Task (Errors)"

    except Exception:
        logger.exception("An exception occurred in task_update_view")

    context = {
        "form": form,
        "task_id": task_id,
        "page_title": page_title,
        "user_labels": Label.objects.filter(owner=request.user),
        "selected_label_ids": [lbl.pk for lbl in form.cleaned_data.get("labels", [])],
    }
    return render(request, template_name=ADD_TASK_TEMPLATE_NAME, context=context)


@require_http_methods(request_method_list=["GET", "POST"])
def task_update_view(request, task_id):
    task = get_task_for_user(user=request.user, task_id=task_id)

    if not task:
        response = hx_location_response(reverse("home"))
        messages.error(request, "No task assiociated with this id.")
        return response

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            return handle_valid_update_form(request, task_id, form)

    form = TaskForm(instance=task, user=request.user)
    page_title = "Update Task"
    context = {
        "form": form,
        "task_id": task_id,
        "page_title": page_title,
        "user_labels": Label.objects.filter(owner=request.user),
        "selected_label_ids": list(task.labels.values_list("pk", flat=True)),
    }
    return render(request, template_name=ADD_TASK_TEMPLATE_NAME, context=context)


@require_http_methods(request_method_list=["GET", "POST"])
def task_detail_view(request, task_id):
    """
    Renders a single task in read-only "view" mode by default.

    Passing ``?mode=edit`` (or submitting the edit form via POST) switches the
    same layout into editable form mode. Successful updates drop back to view
    mode, so the page always opens read-only until the user opts to edit.
    """
    try:
        task = get_task_for_user(user=request.user, task_id=task_id)
    except Task.DoesNotExist:
        messages.error(request, "No task associated with this id.")
        if request.htmx:
            return hx_location_response(reverse("home"))
        raise Http404

    editing = request.method == "POST" or request.GET.get("mode") == "edit"

    form = TaskForm(
        request.POST if request.method == "POST" else None,
        instance=task,
        user=request.user,
    )
    selected_label_ids = list(task.labels.values_list("pk", flat=True))

    if request.method == "POST":
        if form.is_valid():
            try:
                task, success = task_update_service(
                    user=request.user,
                    task_id=task_id,
                    title=form.cleaned_data["title"],
                    description=form.cleaned_data.get("description"),
                    status=form.cleaned_data["status"],
                    priority=form.cleaned_data["priority"],
                    due_datetime=form.cleaned_data.get("due_datetime"),
                    scheduled_date=form.cleaned_data.get("scheduled_date"),
                    labels=form.cleaned_data.get("labels"),
                )
            except DueDateInPastError as e:
                form.add_error("due_datetime", f"{e}")
            except ScheduledDateInPastError as e:
                form.add_error("scheduled_date", f"{e}")
            except Exception:
                logger.exception("An exception occurred in task_detail_view")
            else:
                if success:
                    messages.success(request, "Task updated successfully.")
                else:
                    messages.warning(request, "No changes were made to the task.")
                editing = False
                form = TaskForm(instance=task, user=request.user)
                selected_label_ids = list(task.labels.values_list("pk", flat=True))
        else:
            selected_label_ids = [lbl.pk for lbl in form.cleaned_data.get("labels", [])]

    context = {
        "task": task,
        "form": form,
        "editing": editing,
        "user_labels": Label.objects.filter(owner=request.user),
        "selected_label_ids": selected_label_ids,
        "Status": Task.Status,
        "Priority": Task.Priority,
    }
    if request.htmx and not request.htmx.boosted:
        return render(request, "todo/partials/_task_detail.html", context)
    return render(request, "todo/task_detail.html", context)


@require_http_methods(request_method_list=["POST"])
def task_delete_view(request, task_id):
    try:
        task_delete_service(user=request.user, task_id=task_id)
        messages.success(request, message="Task deleted successfully.")
    except Exception:
        messages.warning(
            request, message="An error occurred, no changes have been made"
        )

    response = hx_location_response(reverse("home"))
    return response


@require_http_methods(request_method_list=["GET"])
def all_tasks_view(request):
    filters = {
        "query": request.GET.get("q", "").strip() or None,
        "status": parse_status_param(request.GET.get("status")),
        "priority": parse_priority_param(request.GET.get("priority")),
        "label_id": parse_label_param(request.user, request.GET.get("label")),
        "due_from": parse_date_param(request.GET.get("due_from")),
        "due_to": parse_date_param(request.GET.get("due_to")),
    }
    filters_active = any(
        request.GET.get(key, "").strip()
        for key in ("q", "status", "priority", "label", "due_from", "due_to")
    )

    tasks = search_tasks_for_user(user=request.user, **filters)
    page_obj, prev_page_url, next_page_url = paginate_tasks(request, tasks)

    context = {
        "all_tasks": page_obj.object_list,
        "page_obj": page_obj,
        "prev_page_url": prev_page_url,
        "next_page_url": next_page_url,
        "page_base_url": reverse("all_tasks"),
        "filters_active": filters_active,
        "show_filters": True,
        "user_labels": Label.objects.filter(owner=request.user).order_by("name"),
        "page_title": "All Tasks",
        "Status": Task.Status,
        "Priority": Task.Priority,
    }
    if request.htmx and not request.htmx.boosted:
        return render(
            request=request,
            template_name="todo/partials/_all_tasks_list.html",
            context=context,
        )
    return render(
        request=request,
        template_name="todo/all_tasks.html",
        context=context,
    )


@require_http_methods(["GET"])
def refresh_task_labels_view(request):
    user_labels = Label.objects.filter(owner=request.user)
    form_labels = request.GET.get("form_labels", "")
    selected_ids = [int(x) for x in form_labels.split(",") if x] if form_labels else []
    context = {"user_labels": user_labels, "selected_ids": selected_ids}
    return render(request, "todo/partials/_labels_selector.html", context)


@require_http_methods(["GET"])
def task_list_by_label_view(request, label_id):
    tasks = get_tasks_by_label(user=request.user, label_id=label_id)
    label = get_object_or_404(request.user.labels, id=label_id)
    page_obj, prev_page_url, next_page_url = paginate_tasks(request, tasks)

    context = {
        "all_tasks": page_obj.object_list,
        "page_obj": page_obj,
        "prev_page_url": prev_page_url,
        "next_page_url": next_page_url,
        "page_base_url": reverse("tasks_by_label", args=[label_id]),
        "page_title": f"Tasks labeled '{label.name}'",
        "Status": Task.Status,
        "Priority": Task.Priority,
    }
    if request.htmx and not request.htmx.boosted:
        return render(
            request=request,
            template_name="todo/partials/_all_tasks_list.html",
            context=context,
        )
    return render(
        request=request,
        template_name="todo/all_tasks.html",
        context=context,
    )
