from django import forms
from django.core.exceptions import ValidationError
from .models import Label

LABEL_COLORS = [
    "#EF4444",
    "#F97316",
    "#F59E0B",
    "#EAB308",
    "#84CC16",
    "#22C55E",
    "#10B981",
    "#14B8A6",
    "#06B6D4",
    "#0EA5E9",
    "#3B82F6",
    "#6366F1",
    "#8B5CF6",
    "#A855F7",
    "#D946EF",
    "#EC4899",
    "#F43F5E",
    "#78716C",
    "#1E293B",
    "#0F172A",
]


class LabelForm(forms.ModelForm):
    color = forms.CharField(widget=forms.HiddenInput)

    def clean_color(self):
        color = self.cleaned_data.get("color")
        if color not in LABEL_COLORS:
            raise ValidationError("Please select a valid color.")
        return color

    class Meta:
        model = Label
        fields = ["name", "color"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "input w-full",
                    "placeholder": "e.g. Bug, Feature, Urgent",
                }
            ),
        }
