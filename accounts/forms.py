from django import forms
from django.contrib.auth.forms import AuthenticationForm


class CustomLoginForm(AuthenticationForm):
    login_input_classes = "form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#1c170d] focus:outline-0 focus:ring-0 border border-[#e8e1cf] bg-[#fcfbf8] focus:border-[#e8e1cf] h-14 placeholder:text-[#9b844b] p-[15px] text-base font-normal leading-normal"

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
