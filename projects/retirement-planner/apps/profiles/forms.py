import datetime
from django import forms
from .models import UserProfile, SpouseProfile


class MonthYearInput(forms.DateInput):
    """Renders as <input type="month"> and formats existing dates as YYYY-MM."""
    input_type = "month"
    format = "%Y-%m"


class MonthYearField(forms.DateField):
    """Accepts YYYY-MM input and stores as the 1st of that month."""
    widget = MonthYearInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("input_formats", ["%Y-%m"])
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        date = super().to_python(value)
        if date and isinstance(date, datetime.date):
            return date.replace(day=1)
        return date


class UserProfileForm(forms.ModelForm):
    birth_date = MonthYearField()
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
    birth_date = MonthYearField()
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
