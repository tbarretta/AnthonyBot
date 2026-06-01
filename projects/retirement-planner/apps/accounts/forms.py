from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Invitation


class AccountSettingsForm(forms.ModelForm):
    """Allow users to update their name and email address."""
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "First name"}),
            "last_name":  forms.TextInput(attrs={"placeholder": "Last name"}),
            "email":      forms.EmailInput(attrs={"placeholder": "you@example.com"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email   # keep username in sync with email
        if commit:
            user.save()
        return user


class InvitationForm(forms.ModelForm):
    """Master Admin form to create a new invitation."""
    class Meta:
        model = Invitation
        fields = ["email"]


class RegisterForm(UserCreationForm):
    """Registration form; only accessible via valid invitation token."""
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        self.invitation = kwargs.pop("invitation", None)
        super().__init__(*args, **kwargs)
        if self.invitation:
            self.fields["email"].initial = self.invitation.email
            self.fields["email"].widget.attrs["readonly"] = True

    def clean_email(self):
        email = self.cleaned_data["email"]
        if self.invitation and email != self.invitation.email:
            raise forms.ValidationError("Email must match the invitation.")
        return email
