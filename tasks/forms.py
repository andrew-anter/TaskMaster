from django import forms

from .models import Task
from labels.models import Label

FORM_FIELD_CLASSES = "input w-full"
SELECT_FIELD_CLASSES = "select w-full"


class DateInput(forms.DateInput):
    input_type = "date"


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"


class TaskForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields["labels"].queryset = Label.objects.filter(owner=user)
        else:
            self.fields["labels"].queryset = Label.objects.none()

    class Meta:
        model = Task
        fields = [
            "title",
            "description",
            "due_datetime",
            "scheduled_date",
            "status",
            "priority",
            "labels",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": FORM_FIELD_CLASSES,
                    "placeholder": "Enter task title",
                    "autofocus": True,
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
            "labels": forms.CheckboxSelectMultiple(
                attrs={
                    "class": "checkbox checkbox-primary",
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
            "labels": "Labels",
        }
