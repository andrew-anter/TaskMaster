from django import forms
from .models import Task

DESIGN_INPUT_CLASSES = "form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#1c170d] focus:outline-0 focus:ring-0 border border-[#e8e1cf] bg-[#fcfbf8] focus:border-[#e8e1cf] h-14 placeholder:text-[#9b844b] p-[15px] text-base font-normal leading-normal"
DESIGN_TEXTAREA_CLASSES = f"{DESIGN_INPUT_CLASSES} min-h-36"
DESIGN_SELECT_CLASSES = (
    f"{DESIGN_INPUT_CLASSES} custom-select appearance-none"  # For select elements
)


class DateInput(forms.DateInput):
    input_type = "date"


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"


class TaskForm(forms.ModelForm):
    # New base classes from your latest design

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
                    "class": DESIGN_INPUT_CLASSES,
                    "placeholder": "Enter task title",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": DESIGN_TEXTAREA_CLASSES,
                    "placeholder": "Add a description",
                    "rows": 5,  # Design has min-h-36, rows is a suggestion
                }
            ),
            "due_datetime": DateTimeInput(
                attrs={
                    "class": DESIGN_INPUT_CLASSES,  # Styled like other inputs
                    "placeholder": "Select due date & time",
                }
            ),
            "scheduled_date": DateInput(
                attrs={  # Using the custom DateInput
                    "class": DESIGN_INPUT_CLASSES,  # Styled like other inputs
                    "placeholder": "Select scheduled date",
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": DESIGN_SELECT_CLASSES,
                }
            ),
            "priority": forms.Select(
                attrs={
                    "class": DESIGN_SELECT_CLASSES,
                }
            ),
        }
        labels = {
            "title": "Task Title",
            "description": "Description",
            "due_datetime": "Due Date & Time",  # Matches design
            "scheduled_date": "Scheduled Date",  # Adding this, was not in new design form explicitly
            "status": "Status",  # Adding this
            "priority": "Priority",  # Adding this
        }
