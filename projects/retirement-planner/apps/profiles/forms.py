from django import forms
from .models import UserProfile, SpouseProfile


class UserProfileForm(forms.ModelForm):
    birth_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    # annual_income rendered as plain text input; JS handles currency formatting
    annual_income = forms.DecimalField(
        max_digits=12, decimal_places=0,
        widget=forms.TextInput(attrs={
            "inputmode": "numeric",
            "data-currency": "true",
            "placeholder": "e.g. 150,000",
        })
    )
    income_growth_rate = forms.DecimalField(
        max_digits=4, decimal_places=1,
        widget=forms.NumberInput(attrs={"step": "0.1", "min": "0", "max": "20"})
    )

    class Meta:
        model = UserProfile
        fields = [
            "birth_date", "state", "filing_status",
            "annual_income", "income_growth_rate",
            "life_expectancy_age",
        ]


class SpouseProfileForm(forms.ModelForm):
    birth_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    annual_income = forms.DecimalField(
        max_digits=12, decimal_places=0,
        widget=forms.TextInput(attrs={
            "inputmode": "numeric",
            "data-currency": "true",
            "placeholder": "e.g. 100,000",
        })
    )
    income_growth_rate = forms.DecimalField(
        max_digits=4, decimal_places=1,
        widget=forms.NumberInput(attrs={"step": "0.1", "min": "0", "max": "20"})
    )

    class Meta:
        model = SpouseProfile
        fields = [
            "first_name", "birth_date",
            "annual_income", "income_growth_rate",
            "life_expectancy_age",
        ]
