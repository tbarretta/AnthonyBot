from django import forms
from .models import InvestmentAccount


class InvestmentAccountForm(forms.ModelForm):
    class Meta:
        model = InvestmentAccount
        fields = [
            "name", "account_type", "owner",
            "current_balance", "annual_contribution",
            "employer_match_pct", "employer_match_limit_pct",
            "asset_allocation_stocks", "asset_allocation_bonds",
            "expected_pension_annual", "pension_start_age",
            "is_active",
        ]

    def clean(self):
        cleaned_data = super().clean()
        stocks = cleaned_data.get("asset_allocation_stocks", 0)
        bonds = cleaned_data.get("asset_allocation_bonds", 0)
        if stocks + bonds != 100:
            raise forms.ValidationError("Stock + bond allocation must equal 100%.")
        return cleaned_data
