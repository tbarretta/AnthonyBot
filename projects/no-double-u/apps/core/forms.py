from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class HoneypotUserCreationForm(UserCreationForm):
    # This field is meant to catch bots. Humans won't see it (hidden via CSS).
    website_url = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'autocomplete': 'off', 'tabindex': '-1'})
    )

    class Meta(UserCreationForm.Meta):
        model = User

    def clean(self):
        cleaned_data = super().clean()
        website_url = cleaned_data.get('website_url')
        
        # If the honeypot field is filled out, we silently reject it by raising a validation error.
        # We can make the error obscure so bots don't realize they hit a honeypot.
        if website_url:
            raise forms.ValidationError("Registration failed. Please try again.")
            
        return cleaned_data
