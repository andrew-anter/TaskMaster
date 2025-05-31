from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse

from .forms import TaskForm
from .models import Task

from .services import add_todo_service
from .selectors import get_todo_items, get_upcoming_tasks


def task_list_view(request):
    my_tasks = get_todo_items()
    upcoming_tasks = get_upcoming_tasks()

    context = {
        "my_tasks": my_tasks,
        "upcoming_tasks": upcoming_tasks,
        "Priority": Task.Priority,
        "Status": Task.Status,
        "page_title": "My Tasks",
    }
    return render(request, "todo/todo_list.html", context)


def task_add_view(request):
    form = TaskForm()
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            try:
                add_todo_service(
                    title=form.cleaned_data["title"],
                    description=form.cleaned_data.get("description"),
                    status=form.cleaned_data["status"],
                    priority=form.cleaned_data["priority"],
                    due_date=form.cleaned_data.get("due_date"),
                    scheduled_date=form.cleaned_data.get("scheduled_date"),
                )
                messages.success(request, "Task added successfully!")
                return redirect(reverse("todo_list"))
            except Exception as e:
                messages.error(request, f"Could not add task: {e}")
        else:
            messages.error(request, "Please correct the errors below.")

    context = {
        "form": form,
        "page_title": "Add task",
    }
    return render(request=request, template_name="todo/add_task.html", context=context)


def task_mark_as_completed_view(request, item_id):
    item = get_object_or_404(Task, id=item_id)
    if request.method == "POST":
        item.status = Task.Status.COMPLETED
        item.save()
        messages.info(request, f"Task '{item.title}' status updated.")
        return HttpResponseRedirect(reverse("todo_list"))
    return HttpResponseRedirect(reverse("todo_list"))


def task_delete_view(request, item_id):
    item = get_object_or_404(Task, id=item_id)
    if request.method == "POST":
        item_title = item.title
        item.delete()
        messages.warning(request, f"Task '{item_title}' deleted.")
        return HttpResponseRedirect(reverse("todo_list"))
    return HttpResponseRedirect(reverse("todo_list"))
