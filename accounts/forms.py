from django import forms
from django.contrib.auth.forms import AuthenticationForm


class CustomLoginForm(AuthenticationForm):
    login_input_classes = "input input-bordered w-full h-14 p-[15px] text-base"

    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": login_input_classes,
                "placeholder": "Email or Username",
                "autofocus": True,
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": login_input_classes,
                "placeholder": "Password",
            }
        )
    )
