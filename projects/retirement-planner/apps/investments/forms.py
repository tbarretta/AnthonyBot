from django import forms
from .models import InvestmentAccount, IncomeSource


class InvestmentAccountForm(forms.ModelForm):
    class Meta:
        model = InvestmentAccount
        fields = [
            "name", "account_type", "owner",
            "current_balance", "annual_contribution",
            "employer_match_pct", "employer_match_limit_pct",
            "asset_allocation_stocks", "asset_allocation_bonds",
            "is_active",
        ]

    def clean(self):
        cleaned_data = super().clean()
        stocks = cleaned_data.get("asset_allocation_stocks", 0)
        bonds = cleaned_data.get("asset_allocation_bonds", 0)
        if stocks + bonds != 100:
            raise forms.ValidationError("Stock + bond allocation must equal 100%.")
        return cleaned_data


class IncomeSourceForm(forms.ModelForm):
    class Meta:
        model = IncomeSource
        fields = [
            "name", "source_type", "owner",
            # SS-specific
            "ss_monthly_at_62", "ss_monthly_at_67", "ss_monthly_at_70", "ss_cola_rate",
            # Non-SS
            "annual_amount", "start_age", "end_age",
            # Growth / inflation
            "is_inflation_adjusted", "inflation_rate_override",
            # Tax
            "is_taxable", "tax_rate_override",
            # Pension survivor
            "survivor_benefit_pct",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make SS fields optional — they are only required for social_security type
        for field in ["ss_monthly_at_62", "ss_monthly_at_67", "ss_monthly_at_70"]:
            self.fields[field].required = False
        # Non-SS overrides are always optional
        for field in ["end_age", "inflation_rate_override", "tax_rate_override", "survivor_benefit_pct"]:
            self.fields[field].required = False

    def clean(self):
        cleaned_data = super().clean()
        source_type = cleaned_data.get("source_type")
        if source_type == "social_security":
            at_62 = cleaned_data.get("ss_monthly_at_62")
            at_67 = cleaned_data.get("ss_monthly_at_67")
            at_70 = cleaned_data.get("ss_monthly_at_70")
            if not any([at_62, at_67, at_70]):
                raise forms.ValidationError(
                    "For Social Security, enter at least one monthly benefit estimate "
                    "(at 62, 67, or 70)."
                )
        return cleaned_data
