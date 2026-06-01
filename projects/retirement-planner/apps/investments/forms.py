from django import forms
from .models import InvestmentAccount, IncomeSource


class CommaDecimalField(forms.DecimalField):
    """DecimalField that accepts comma-formatted numbers like 1,250,000."""

    def to_python(self, value):
        if isinstance(value, str):
            value = value.replace(",", "")
        return super().to_python(value)


class InvestmentAccountForm(forms.ModelForm):
    current_balance = CommaDecimalField(
        max_digits=14, decimal_places=0,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "data-currency": "true", "placeholder": "0"})
    )
    annual_contribution = CommaDecimalField(
        max_digits=10, decimal_places=0,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "data-currency": "true", "placeholder": "0"})
    )
    employer_match_pct = forms.IntegerField(
        min_value=0, max_value=100, required=False, initial=0,
        widget=forms.NumberInput(attrs={"step": "1", "min": "0", "max": "100", "placeholder": "0"})
    )
    asset_allocation_stocks = forms.IntegerField(
        min_value=0, max_value=100,
        widget=forms.NumberInput(attrs={"step": "1", "min": "0", "max": "100", "placeholder": "80"})
    )
    asset_allocation_bonds = forms.IntegerField(
        min_value=0, max_value=100,
        widget=forms.NumberInput(attrs={"step": "1", "min": "0", "max": "100", "placeholder": "20"})
    )

    class Meta:
        model = InvestmentAccount
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Tom's 401(k) at Fidelity"}),
        }
        fields = [
            "name", "account_type", "owner",
            "current_balance", "annual_contribution",
            "employer_match_pct",
            "asset_allocation_stocks", "asset_allocation_bonds",
            "is_active",
        ]

    def clean(self):
        cleaned_data = super().clean()
        stocks = cleaned_data.get("asset_allocation_stocks")
        bonds = cleaned_data.get("asset_allocation_bonds")
        if stocks is not None and bonds is not None and stocks + bonds != 100:
            raise forms.ValidationError("Stock + bond allocation must equal 100%.")
        return cleaned_data


class IncomeSourceForm(forms.ModelForm):
    class Meta:
        model = IncomeSource
        fields = [
            "name", "source_type", "owner",
            # SS-specific
            "ss_monthly_at_67", "ss_cola_rate",
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
            "name": forms.TextInput(attrs={"placeholder": "e.g. Tom's SS, Rental - 123 Main St"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # SS fields optional — only required when source_type == social_security
        self.fields["ss_monthly_at_67"].required = False
        # Non-SS overrides are always optional
        for field in ["end_age", "inflation_rate_override", "tax_rate_override", "survivor_benefit_pct"]:
            self.fields[field].required = False

    def clean(self):
        cleaned_data = super().clean()
        source_type = cleaned_data.get("source_type")
        if source_type == "social_security":
            at_67 = cleaned_data.get("ss_monthly_at_67")
            if not at_67:
                raise forms.ValidationError(
                    "For Social Security, enter your full monthly benefit at age 67 "
                    "(from your SSA statement at ssa.gov/myaccount)."
                )
        return cleaned_data
