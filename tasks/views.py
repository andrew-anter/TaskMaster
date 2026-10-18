from datetime import date
from urllib.parse import quote as url_quote

from django.contrib import messages
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from common.http import hx_location_response, is_partial_request
from common.pagination import paginate
from labels.context import build_label_detail_context
from labels.models import Label

from .exceptions import DueDateInPastError, ScheduledDateInPastError
from .forms import TaskForm
from .models import Task
from .selectors import (
    OVERDUE_TASKS_LIMIT,
    SORTABLE_FIELDS,
    get_overdue_tasks_count_for_user,
    get_overdue_tasks_for_user,
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

ADD_TASK_TEMPLATE_NAME = "todo/partials/_add_task.html"
TASKS_PER_PAGE = 25

# ``origin`` values travel with every row's mutating form, so the views can
# re-render exactly the region the request came from (and keep filters, sort
# and pagination of that region intact).
ORIGIN_DASHBOARD = "dashboard"
ORIGIN_ALL_TASKS = "all_tasks"
ORIGIN_LABEL_TASKS = "label_tasks"
ORIGIN_LABEL_DETAIL = "label_detail"
ORIGIN_TASK_DETAIL = "task_detail"


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


def parse_sort_param(value: str | None) -> tuple[str | None, str]:
    """Parses a ``sort`` query param like ``-due_datetime`` into (field, dir).

    Invalid or unknown values fall back to ``(None, "asc")``, leaving the
    queryset on its default ``Meta.ordering``.
    """
    if not value:
        return None, "asc"
    sort_dir = "desc" if value.startswith("-") else "asc"
    field = value.removeprefix("-")
    if field not in SORTABLE_FIELDS:
        return None, "asc"
    return field, sort_dir


def parse_origin(value: str | None) -> tuple[str, int | None]:
    """Splits an ``origin`` value such as ``label_tasks:3`` into key and id."""
    key, _, raw_pk = (value or "").partition(":")
    return key, int(raw_pk) if raw_pk.isdigit() else None


def origin_value(key: str, pk: int | None = None) -> str:
    """Builds an ``origin`` value for a list region."""
    return f"{key}:{pk}" if pk is not None else key


# -- Context builders (shared by the pages and the region re-renders) -- #
def dashboard_context(request) -> dict:
    """Context for the home dashboard sections."""
    today_page_obj, prev_page_url, next_page_url = paginate(
        request, get_today_tasks_for_user(user=request.user), page_size=TASKS_PER_PAGE
    )
    return {
        "today_tasks": today_page_obj.object_list,
        "upcoming_tasks": get_upcoming_tasks_for_user(user=request.user),
        "upcoming_tasks_url": f"{reverse('all_tasks')}?sort=due_datetime",
        "overdue_tasks": get_overdue_tasks_for_user(user=request.user),
        "overdue_tasks_limit": OVERDUE_TASKS_LIMIT,
        "overdue_tasks_total": get_overdue_tasks_count_for_user(user=request.user),
        "page_obj": today_page_obj,
        "prev_page_url": prev_page_url,
        "next_page_url": next_page_url,
        "page_base_url": reverse("home"),
        "origin": ORIGIN_DASHBOARD,
        "Status": Task.Status,
        "Priority": Task.Priority,
        "page_title": "My Tasks",
    }


def all_tasks_context(request, *, label=None) -> dict:
    """Context for the task list region (all tasks, or the tasks of one label)."""
    filters = {
        "query": request.GET.get("q", "").strip() or None,
        "status": parse_status_param(request.GET.get("status")),
        "priority": parse_priority_param(request.GET.get("priority")),
        "label_id": parse_label_param(request.user, request.GET.get("label")),
        "due_from": parse_date_param(request.GET.get("due_from")),
        "due_to": parse_date_param(request.GET.get("due_to")),
    }
    sort_by, sort_dir = parse_sort_param(request.GET.get("sort"))
    filters_active = any(
        request.GET.get(key, "").strip()
        for key in ("q", "status", "priority", "label", "due_from", "due_to")
    )

    if label is None:
        tasks = search_tasks_for_user(
            user=request.user, **filters, sort_by=sort_by, sort_dir=sort_dir
        )
        page_base_url = reverse("all_tasks")
        origin = ORIGIN_ALL_TASKS
        page_title = "All Tasks"
    else:
        tasks = get_tasks_by_label(user=request.user, label_id=label.pk)
        page_base_url = reverse("tasks_by_label", args=[label.pk])
        origin = origin_value(ORIGIN_LABEL_TASKS, label.pk)
        page_title = f"Tasks labeled '{label.name}'"

    page_obj, prev_page_url, next_page_url = paginate(
        request, tasks, page_size=TASKS_PER_PAGE
    )

    return {
        "all_tasks": page_obj.object_list,
        "page_obj": page_obj,
        "prev_page_url": prev_page_url,
        "next_page_url": next_page_url,
        "page_base_url": page_base_url,
        "filters_active": filters_active,
        "show_filters": label is None,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
        "user_labels": Label.objects.filter(owner=request.user).order_by("name"),
        "label": label,
        "origin": origin,
        "Status": Task.Status,
        "Priority": Task.Priority,
        "page_title": page_title,
    }


def task_detail_context(
    request, task, *, editing: bool = False, form=None, selected_label_ids=None
) -> dict:
    """Context for the single-task view/form."""
    if form is None:
        form = TaskForm(instance=task, user=request.user)
    if selected_label_ids is None:
        selected_label_ids = list(task.labels.values_list("pk", flat=True))
    return {
        "task": task,
        "form": form,
        "editing": editing,
        "user_labels": Label.objects.filter(owner=request.user),
        "selected_label_ids": selected_label_ids,
        "Status": Task.Status,
        "Priority": Task.Priority,
        "page_title": task.title,
    }


def render_task_region(request) -> HttpResponse:
    """Re-render the list region a mutating request came from."""
    key, pk = parse_origin(request.POST.get("origin"))

    if key == ORIGIN_DASHBOARD:
        return render(
            request, "todo/partials/_dashboard_lists.html", dashboard_context(request)
        )

    if key == ORIGIN_LABEL_TASKS and pk is not None:
        label = request.user.labels.filter(pk=pk).first()
        if label is not None:
            return render(
                request,
                "todo/partials/_tasks_region.html",
                all_tasks_context(request, label=label),
            )

    if key == ORIGIN_LABEL_DETAIL and pk is not None:
        label = request.user.labels.filter(pk=pk).first()
        if label is not None:
            return render(
                request,
                "labels/partials/_label_detail_tasks.html",
                build_label_detail_context(user=request.user, label=label),
            )

    if key == ORIGIN_TASK_DETAIL and pk is not None:
        task = Task.objects.filter(pk=pk, owner=request.user).first()
        if task is not None:
            return render(
                request,
                "todo/partials/_task_detail.html",
                task_detail_context(request, task),
            )

    return render(
        request, "todo/partials/_tasks_region.html", all_tasks_context(request)
    )


def region_redirect_url(request) -> str:
    """Non-HTMX fallback target for a mutating request (POST/redirect/GET)."""
    key, pk = parse_origin(request.POST.get("origin"))
    if key == ORIGIN_DASHBOARD:
        return reverse("home")
    if key == ORIGIN_LABEL_TASKS and pk is not None:
        return reverse("tasks_by_label", args=[pk])
    if key == ORIGIN_LABEL_DETAIL and pk is not None:
        return reverse("label_detail", args=[pk])
    if key == ORIGIN_TASK_DETAIL and pk is not None:
        return reverse("task_detail", args=[pk])
    return reverse("all_tasks")


@require_http_methods(["GET"])
def task_list_view(request):
    context = dashboard_context(request)
    if is_partial_request(request):
        return render(request, "todo/partials/_task_list.html", context)
    return render(request, "todo/task_list.html", context)


@require_http_methods(request_method_list=["GET", "POST"])
def task_add_partial_view(request):
    template_name = ADD_TASK_TEMPLATE_NAME
    raw_next = request.POST.get("next") or request.GET.get("next", "")
    if raw_next.startswith("/") and not raw_next.startswith("//"):
        next_url = raw_next
    else:
        next_url = ""
    add_task_base_url = reverse("task_add")
    add_task_url = (
        f"{add_task_base_url}?next={url_quote(next_url)}"
        if next_url
        else add_task_base_url
    )

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
            except (DueDateInPastError, ScheduledDateInPastError, ValueError) as e:
                form.add_error(None, f"{e}")
            else:
                redirect_target = next_url or reverse("home")
                messages.success(request, "Task added successfully.")
                if request.htmx:
                    return hx_location_response(redirect_target)
                return HttpResponseRedirect(redirect_target)

        if request.htmx:
            context = {
                "form": form,
                "page_title": "Add New Task",
                "user_labels": Label.objects.filter(owner=request.user),
                "selected_label_ids": [
                    lbl.pk for lbl in form.cleaned_data.get("labels", [])
                ],
                "add_task_url": add_task_url,
                "next_url": next_url,
            }
            return render(request, template_name, context)

    else:
        form = TaskForm(user=request.user)

    context = {
        "form": form,
        "page_title": "Add New Task",
        "user_labels": Label.objects.filter(owner=request.user),
        "selected_label_ids": [],
        "add_task_url": add_task_url,
        "next_url": next_url,
    }
    if is_partial_request(request):
        return render(request, template_name, context)
    return render(request, "todo/task_add.html", context)


@require_http_methods(request_method_list=["POST"])
def task_update_status_view(request, task_id):
    try:
        task = get_task_for_user(user=request.user, task_id=task_id)
    except Task.DoesNotExist:
        messages.error(request, "No task associated with this id.")
        if request.htmx:
            return hx_location_response(reverse("home"))
        raise Http404
    toggle_task_status_service(task=task)

    if request.htmx:
        return render_task_region(request)

    messages.info(request, f"Task '{task.title}' status updated.")
    return HttpResponseRedirect(region_redirect_url(request))


@require_http_methods(request_method_list=["GET", "POST"])
def task_detail_view(request, task_id):
    """
    Renders a single task in read-only "view" mode by default.

    Passing ``?mode=edit`` (or submitting the edit form via POST) switches the
    same layout into editable form mode. Successful updates drop back to view
    mode and replace the ``?mode=edit`` URL, so reloading the page always opens
    read-only until the user opts to edit again.
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
            except ValueError as e:
                form.add_error(None, f"{e}")
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

    context = task_detail_context(
        request,
        task,
        editing=editing,
        form=form,
        selected_label_ids=selected_label_ids,
    )
    if is_partial_request(request):
        response = render(request, "todo/partials/_task_detail.html", context)
        if request.method == "POST" and not editing:
            # Leave edit mode in the address bar as well, so a reload shows the
            # read-only view instead of the form again.
            response["HX-Replace-Url"] = reverse("task_detail", args=[task.pk])
        return response
    return render(request, "todo/task_detail.html", context)


@require_http_methods(request_method_list=["POST"])
def task_delete_view(request, task_id):
    try:
        task_delete_service(user=request.user, task_id=task_id)
    except Task.DoesNotExist:
        messages.error(request, "No task associated with this id.")
        if request.htmx:
            return hx_location_response(reverse("home"))
        raise Http404
    messages.success(request, message="Task deleted successfully.")

    if request.htmx:
        key, _ = parse_origin(request.POST.get("origin"))
        if key == ORIGIN_TASK_DETAIL:
            # The task no longer exists: leave its detail page.
            return hx_location_response(reverse("home"))
        return render_task_region(request)

    return HttpResponseRedirect(region_redirect_url(request))


@require_http_methods(request_method_list=["GET"])
def all_tasks_view(request):
    context = all_tasks_context(request)
    if is_partial_request(request):
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
def task_list_by_label_view(request, label_id):
    label = get_object_or_404(request.user.labels, id=label_id)
    context = all_tasks_context(request, label=label)
    if is_partial_request(request):
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
