from django import forms

from .models import Task

FORM_FIELD_CLASSES = "input w-full"
SELECT_FIELD_CLASSES = "select w-full"


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
            "due_datetime",
            "scheduled_date",
            "status",
            "priority",
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
                    "class": "textarea h-36 w-full",  # Keep min-h-36 for textarea
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
