from allauth.account.fields import EmailField
from allauth.account.forms import ResetPasswordForm, ResetPasswordKeyForm, SignupForm
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UsernameField

AUTOCOMPLETE_BY_FIELD = {
    "username": "username",
    "email": "email",
    "password1": "new-password",
    "password2": "new-password",
}


def add_autocomplete_hints(form: forms.BaseForm) -> None:
    """Hint password managers/browser autofill for the fields the form has."""
    for name, value in AUTOCOMPLETE_BY_FIELD.items():
        field = form.fields.get(name)
        if field is not None:
            field.widget.attrs.setdefault("autocomplete", value)


class CustomLoginForm(AuthenticationForm):
    login_input_classes = "input input-bordered w-full h-14 p-[15px] text-base"

    username = UsernameField(
        widget=forms.TextInput(
            attrs={
                "class": login_input_classes,
                "placeholder": "Email or Username",
                "autocomplete": "username",
                "autofocus": True,
            }
        )
    )
    password = forms.CharField(
        # Django's own login field: passwords may legitimately have edge spaces.
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": login_input_classes,
                "placeholder": "Password",
                "autocomplete": "current-password",
            }
        ),
    )


class CustomRegisterForm(SignupForm):
    login_input_classes = "input input-bordered w-full h-14 p-[15px] text-base"
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": login_input_classes,
                "placeholder": "Username",
                "autocomplete": "username",
                "autofocus": True,
            }
        )
    )

    # allauth's field: EmailValidator + max_length, and lowercases the value.
    email = EmailField(
        max_length=254,
        widget=forms.TextInput(
            attrs={
                "type": "email",
                "class": login_input_classes,
                "placeholder": "Email",
                "autocomplete": "email",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_autocomplete_hints(self)


class CustomResetPasswordForm(ResetPasswordForm):
    input_classes = "input input-bordered w-full h-14 p-[15px] text-base"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs["class"] = self.input_classes
        add_autocomplete_hints(self)


class CustomResetPasswordKeyForm(ResetPasswordKeyForm):
    input_classes = "input input-bordered w-full h-14 p-[15px] text-base"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = self.input_classes
        add_autocomplete_hints(self)
