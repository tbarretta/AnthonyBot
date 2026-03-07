from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, GUARDIAN_RELATIONSHIP_CHOICES


class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "you@example.com", "autofocus": True}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "••••••••"}))

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        self._user = None

    def clean(self):
        email = self.cleaned_data.get("email")
        password = self.cleaned_data.get("password")
        if email and password:
            self._user = authenticate(self.request, username=email, password=password)
            if self._user is None:
                raise forms.ValidationError("Invalid email or password.")
            if not self._user.is_email_verified:
                raise forms.ValidationError(
                    "Please verify your email address before signing in. "
                    "Check your inbox for a verification link."
                )
        return self.cleaned_data

    def get_user(self):
        return self._user


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Min 8 chars, letters + numbers"}),
        label="Password",
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm password"}),
        label="Confirm Password",
    )

    class Meta:
        model = User
        fields = ["name", "email"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "How family members will see you"}),
            "email": forms.EmailInput(attrs={"placeholder": "your@email.com"}),
        }
        help_texts = {
            "name": "Visible to all family members in your registry.",
            "email": "Must be unique. A verification link will be sent here.",
        }

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password")
        p2 = cleaned.get("password_confirm")
        if p1 and p2 and p1 != p2:
            self.add_error("password_confirm", "Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.is_email_verified = False
        user.is_active = True
        if commit:
            user.save()
        return user


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "you@example.com"}))


class SetNewPasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "New password"}))
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Confirm password"}))

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password")
        p2 = cleaned.get("password_confirm")
        if p1 and p2 and p1 != p2:
            self.add_error("password_confirm", "Passwords do not match.")
        return cleaned


class NotificationPreferenceForm(forms.Form):
    notify_on_access_request = forms.BooleanField(required=False, label="Access requests to my wishlist")


class ManagedMemberForm(forms.Form):
    name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Emma or Grandma Rose"}),
        label="Name",
        help_text="Visible to all family members.",
    )
    relationship = forms.ChoiceField(
        choices=GUARDIAN_RELATIONSHIP_CHOICES,
        label="Relationship",
    )
