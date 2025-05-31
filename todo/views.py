from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse

from .forms import TodoItemForm
from .models import TodoItem

from .services import add_todo_service
from .selectors import get_todo_items


def todo_list_view(request):
    todo_items = get_todo_items()
    form = TodoItemForm()

    context = {
        "items": todo_items,
        "form": form,
        "page_title": "My ToDo List",
    }

    return render(request=request, template_name="todo/todo_list.html", context=context)


def add_todo_view(request):
    if request.method == "POST":
        form = TodoItemForm(request.POST)
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
                "page_title": "My To-Do List",
            }
            return render(request, "todo/todo_list.html", context)

    return HttpResponseRedirect(reverse("todo_list"))


def mark_item_as_completed(request, item_id):
    item = get_object_or_404(TodoItem, id=item_id)
    if request.method == "POST":
        item.status = TodoItem.Status.COMPLETED
        item.save()
        messages.info(request, f"Task '{item.title}' status updated.")
        return HttpResponseRedirect(reverse("todo_list"))
    return HttpResponseRedirect(reverse("todo_list"))


def delete_todo_view(request, item_id):
    item = get_object_or_404(TodoItem, id=item_id)
    if request.method == "POST":
        item_title = item.title
        item.delete()
        messages.warning(request, f"Task '{item_title}' deleted.")
        return HttpResponseRedirect(reverse("todo_list"))
    return HttpResponseRedirect(reverse("todo_list"))
