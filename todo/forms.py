# todo/forms.py
from django import forms
from .models import Task


# Custom widgets for better date/time input experience
class DateInput(forms.DateInput):
    input_type = "date"
    # format = '%Y-%m-%d' # Default format is usually fine


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"
    # format = '%Y-%m-%dT%H:%M' # Default format is usually fine


BASE_INPUT_CLASSES = "form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#1a170f] focus:outline-0 focus:ring-0 border-none bg-[#f2efe9] focus:border-none h-14 placeholder:text-[#8f7f56] p-4 text-base font-normal leading-normal"
DATE_INPUT_IN_GROUP_CLASSES = "form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden text-[#1a170f] focus:outline-0 focus:ring-0 border-none bg-transparent focus:border-none h-14 placeholder:text-[#8f7f56] p-4 rounded-r-none border-r-0 pr-2 text-base font-normal leading-normal"


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
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
                    "class": f"{BASE_INPUT_CLASSES}",
                    "placeholder": "Enter task title",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": f"{BASE_INPUT_CLASSES} min-h-36",  # Added min-h-36
                    "placeholder": "Add a description",
                    "rows": 4,  # Adjust rows as needed, though min-h will dominate
                }
            ),
            "due_date": DateTimeInput(
                attrs={  # Using the custom DateTimeInput
                    "class": f"{DATE_INPUT_IN_GROUP_CLASSES}",
                    "placeholder": "Select due date & time",
                }
            ),
            "scheduled_date": DateInput(
                attrs={  # Using the custom DateInput
                    "class": f"{DATE_INPUT_IN_GROUP_CLASSES}",
                    "placeholder": "Select scheduled date",
                }
            ),
            "status": forms.Select(
                attrs={
                    # Added 'custom-select' for the arrow defined in add_task.html's <style>
                    "class": f"{BASE_INPUT_CLASSES} custom-select appearance-none",
                }
            ),
            "priority": forms.Select(
                attrs={
                    "class": f"{BASE_INPUT_CLASSES} custom-select appearance-none",
                }
            ),
        }
        labels = {
            "title": "Task Title",  # Design uses "Task Title"
            "description": "Description",
            "due_date": "Due Date",  # Design uses "Due Date"
            "scheduled_date": "Scheduled Date",  # Added for consistency
            "status": "Status",  # Added for consistency
            "priority": "Priority",  # Added for consistency
        }
