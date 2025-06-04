# todo/forms.py
from django import forms
from .models import Task


FORM_FIELD_CLASSES = (
    "input input-bordered w-full h-14 p-[15px] text-base focus:outline-offset-0"
)
SELECT_FIELD_CLASSES = "select select-bordered w-full h-14 text-base custom-select"


class DateInput(forms.DateInput):
    input_type = "date"


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            "title",
            "description",
            "status",
            "priority",
            "due_datetime",
            "scheduled_date",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": FORM_FIELD_CLASSES,
                    "placeholder": "Enter task title",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": f"{FORM_FIELD_CLASSES} min-h-36",  # Keep min-h-36 for textarea
                    "placeholder": "Add a description",
                    "rows": 5,
                }
            ),
            "due_datetime": DateTimeInput(
                attrs={
                    "class": FORM_FIELD_CLASSES,
                    "placeholder": "Select due date & time",  # Placeholder might not show for datetime-local
                }
            ),
            "scheduled_date": DateInput(
                attrs={
                    "class": FORM_FIELD_CLASSES,
                    "placeholder": "Select scheduled date",  # Placeholder might not show for date
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": SELECT_FIELD_CLASSES,
                }
            ),
            "priority": forms.Select(
                attrs={
                    "class": SELECT_FIELD_CLASSES,
                }
            ),
        }
        labels = {  # Using more concise labels that Django's form rendering can use by default
            "title": "Task Title",
            "description": "Description",
            "due_datetime": "Due Date & Time",
            "scheduled_date": "Scheduled Date",
            "status": "Status",
            "priority": "Priority",
        }
