from django import forms
from .models import TodoItem


# Custom widgets for better date/time input experience
class DateInput(forms.DateInput):
    input_type = "date"


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"


class TodoItemForm(forms.ModelForm):
    class Meta:
        model = TodoItem
        fields = [
            "title",
            "description",
            "status",
            "priority",
            "due_date",
            "scheduled_date",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "Enter task title...",
                    "class": "input input-bordered w-full text-sm",
                    "aria-label": "Task Title",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "placeholder": "Enter task description (optional)...",
                    "class": "textarea textarea-bordered w-full text-sm leading-relaxed",
                    "rows": 3,
                    "aria-label": "Task Description",
                }
            ),
            "due_date": DateTimeInput(
                attrs={
                    "class": "input input-bordered w-full text-sm",
                    "aria-label": "Due Date",
                }
            ),
            "scheduled_date": DateInput(
                attrs={
                    "class": "input input-bordered w-full text-sm",
                    "aria-label": "Scheduled Date",
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "select select-bordered w-full text-sm",
                    "aria-label": "Status",
                }
            ),
            "priority": forms.Select(
                attrs={
                    "class": "select select-bordered w-full text-sm",
                    "aria-label": "Priority",
                }
            ),
        }
        labels = {
            "title": "Title",
            "description": "Description",
            "due_date": "Due Date & Time",
            "scheduled_date": "Scheduled For",
            "status": "Status",
            "priority": "Priority",
        }
