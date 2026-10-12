from django import forms


from django.contrib.auth.forms import AuthenticationForm
from allauth.account.forms import ResetPasswordForm, ResetPasswordKeyForm, SignupForm


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


class CustomRegisterForm(SignupForm):
    login_input_classes = "input input-bordered w-full h-14 p-[15px] text-base"
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": login_input_classes,
                "placeholder": "Username",
                "autofocus": True,
            }
        )
    )

    email = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": login_input_classes,
                "placeholder": "Email",
                "autofocus": True,
            }
        )
    )


class CustomResetPasswordForm(ResetPasswordForm):
    input_classes = "input input-bordered w-full h-14 p-[15px] text-base"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs["class"] = self.input_classes


class CustomResetPasswordKeyForm(ResetPasswordKeyForm):
    input_classes = "input input-bordered w-full h-14 p-[15px] text-base"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = self.input_classes
