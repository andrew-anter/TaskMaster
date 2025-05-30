from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import TodoItem
from .forms import TodoItemForm
from django.contrib import messages


def todo_list_view(request):
    items = TodoItem.objects.all()
    form = TodoItemForm()

    context = {
        "items": items,
        "form": form,
        "page_title": "My ToDo List",
    }

    return render(request=request, template_name="todo/todo_list.html", context=context)


def add_todo_view(request):
    if request.method == "POST":
        form = TodoItemForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Task added successfully!")
            return HttpResponseRedirect(reverse("todo_list"))

        else:
            # If form is invalid, re-render the list page with the form and errors
            messages.error(request, "Please correct the errors below.")
            items = TodoItem.objects.all()
            context = {
                "items": items,
                "form": form,  # Pass the invalid form back
                "page_title": "My To-Do List",
            }
            return render(request, "todo/todo_list.html", context)

    # If GET request, redirect to the list view (form is part of list view)
    return HttpResponseRedirect(reverse("todo_list"))


def toggle_todo_view(request, item_id):
    item = get_object_or_404(TodoItem, id=item_id)
    if request.method == "POST":
        item.completed = not item.completed
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
