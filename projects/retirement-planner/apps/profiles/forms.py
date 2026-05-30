from django import forms
from .models import UserProfile, SpouseProfile, SocialSecurityEstimate


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


class SocialSecurityForm(forms.ModelForm):
    class Meta:
        model = SocialSecurityEstimate
        fields = [
            "owner", "monthly_benefit_at_62", "monthly_benefit_at_67",
            "monthly_benefit_at_70", "claim_age", "cola_rate",
        ]
