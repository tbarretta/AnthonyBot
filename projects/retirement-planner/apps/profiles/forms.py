from django import forms
from .models import UserProfile, SpouseProfile


class UserProfileForm(forms.ModelForm):
    birth_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    class Meta:
        model = UserProfile
        fields = [
            "birth_date", "state", "filing_status", "risk_tolerance",
            "annual_income", "income_growth_rate", "target_retirement_age",
            "income_end_age", "life_expectancy_age",
        ]


class SpouseProfileForm(forms.ModelForm):
    birth_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    class Meta:
        model = SpouseProfile
        fields = [
            "first_name", "birth_date", "annual_income", "income_growth_rate",
            "target_retirement_age", "income_end_age", "life_expectancy_age",
        ]
