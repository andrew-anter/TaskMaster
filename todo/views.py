from .services import add_task_service
from .selectors import get_today_tasks, get_upcoming_tasks

from django.shortcuts import render, redirect, get_object_or_404
from django.http import (
    HttpResponse,
    HttpResponseRedirect,
)  # HttpResponse for HX-Redirect
from django.urls import reverse
from django.contrib import messages

from .models import Task
from .forms import TaskForm


def task_list_view(request):
    today_tasks = get_today_tasks()
    upcoming_tasks = get_upcoming_tasks()

    context = {
        "today_tasks": today_tasks,
        "upcoming_tasks": upcoming_tasks,
        "page_title": "My Tasks",
        "Status": Task.Status,
        "Priority": Task.Priority,
    }
    return render(request, "todo/task_list.html", context)


def task_add_view(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            add_task_service(  # Call your service function
                title=form.cleaned_data["title"],
                description=form.cleaned_data.get("description"),
                status=form.cleaned_data["status"],
                priority=form.cleaned_data["priority"],
                due_date=form.cleaned_data.get("due_date"),
                scheduled_date=form.cleaned_data.get("scheduled_date"),
            )

            if request.htmx:
                response = HttpResponse()  # Empty response is fine
                response["HX-Redirect"] = reverse("task_list")
                messages.success(
                    request, "Task added successfully via HTMX!"
                )  # Message will show on redirected page
                return response
            else:
                messages.success(request, "Task added successfully!")
                return HttpResponseRedirect(reverse("task_list"))
        else:  # Form is invalid
            if request.htmx:
                context = {"form": form, "page_title": "Add New Task (Errors)"}
                return render(
                    request, "todo/partials/_add_task_form_wrapper.html", context
                )

    else:  # GET request
        form = TaskForm()

    context = {"form": form, "page_title": "Add New Task"}
    return render(request, "todo/add_task.html", context)


def task_update_status_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.method == "POST":
        if task.status == Task.Status.COMPLETED:
            task.status = (
                Task.Status.TODO
            )  # Or your preferred default incomplete status
        else:
            task.status = Task.Status.COMPLETED
        # task.modified_at = timezone.now() # auto_now=True on modified_at handles this on save()
        task.save()

        if request.htmx:
            # Return the partial template for the updated task item
            context = {
                "task": task,
                "Status": Task.Status,  # Pass enums if used in partial for comparison
                "Priority": Task.Priority,
            }
            return render(request, "todo/partials/_task_list_item.html", context)
        else:
            # Fallback for non-HTMX requests (though this view is primarily for HTMX now)
            messages.info(request, f"Task '{task.title}' status updated.")
            return HttpResponseRedirect(reverse("task_list"))

    # GET requests to this URL are not typical for this action, redirect or show error
    return redirect(reverse("task_list"))


def task_mark_as_completed_view(request, item_id):
    item = get_object_or_404(Task, id=item_id)
    if request.method == "POST":
        item.status = Task.Status.COMPLETED
        item.save()
        messages.info(request, f"Task '{item.title}' status updated.")
        return HttpResponseRedirect(reverse("task_list"))
    return HttpResponseRedirect(reverse("task_list"))


def task_delete_view(request, item_id):
    item = get_object_or_404(Task, id=item_id)
    if request.method == "POST":
        item_title = item.title
        item.delete()
        messages.warning(request, f"Task '{item_title}' deleted.")
        return HttpResponseRedirect(reverse("task_list"))
    return HttpResponseRedirect(reverse("task_list"))
