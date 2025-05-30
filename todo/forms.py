from django import forms
from .models import TodoItem


class TodoItemForm(forms.ModelForm):
    class Meta:
        model = TodoItem
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "Enter task title...",
                    "class": "input input-bordered w-full",  # DaisyUI input class
                    "aria-label": "Task Title",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "placeholder": "Enter task description (optional)...",
                    "class": "textarea textarea-bordered w-full",  # DaisyUI textarea class
                    "rows": 3,
                    "aria-label": "Task Description",
                }
            ),
        }
