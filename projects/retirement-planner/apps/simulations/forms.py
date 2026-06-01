from django import forms
from apps.investments.forms import CommaDecimalField
from .models import Scenario, SimulationType, SpendingStrategy


class ScenarioForm(forms.ModelForm):
    annual_retirement_spending = CommaDecimalField(
        max_digits=12, decimal_places=0,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "data-currency": "true", "placeholder": "0"})
    )
    class Meta:
        model = Scenario
        fields = [
            "name", "description",
            # simulation_type fixed to deterministic — Monte Carlo coming later
            # Retirement ages (moved from profile)
            "retirement_age_self", "retirement_age_spouse",
            "expected_annual_return_stocks", "expected_annual_return_bonds", "inflation_rate",
            "annual_retirement_spending", "spending_growth_rate", "spending_strategy", "withdrawal_rate_pct", "guardrails_enabled",
            # mc_* fields omitted from UI until Monte Carlo is enabled
            "black_swan_enabled", "black_swan_annual_probability",
            "black_swan_min_loss_pct", "black_swan_max_loss_pct", "black_swan_recovery_years",
            # Social Security — claim strategy only; benefit amounts are on Income Sources
            "ss_claim_age_self", "ss_claim_age_spouse",
            "effective_tax_rate_working", "effective_tax_rate_retirement", "capital_gains_rate",
            "user_life_expectancy_age", "spouse_life_expectancy_age",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "spending_strategy": forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop("profile", None)
        super().__init__(*args, **kwargs)

        if self.profile and not self.instance.pk:
            # Pre-fill life expectancy from profile
            self.fields["user_life_expectancy_age"].initial = self.profile.life_expectancy_age
            if self.profile.has_spouse:
                self.fields["spouse_life_expectancy_age"].initial = self.profile.spouse.life_expectancy_age

        # Add helpful hint about where SS amounts live
        self.fields["ss_claim_age_self"].help_text = (
            "Age at which you plan to claim SS (62–70). "
            "Enter your monthly benefit estimates under "
            "<a href='/investments/income/'>Income Sources</a>."
        )
        self.fields["ss_claim_age_spouse"].help_text = (
            "Age at which your spouse plans to claim SS (62–70). "
            "Enter spouse benefit estimates under "
            "<a href='/investments/income/'>Income Sources</a>."
        )

        # Hide spouse claim age if no spouse on profile
        if self.profile and not self.profile.has_spouse:
            self.fields["ss_claim_age_spouse"].widget = forms.HiddenInput()
            self.fields["ss_claim_age_spouse"].required = False
            self.fields["spouse_life_expectancy_age"].widget = forms.HiddenInput()
            self.fields["spouse_life_expectancy_age"].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Always deterministic until Monte Carlo is re-enabled
        instance.simulation_type = "deterministic"
        if commit:
            instance.save()
        return instance
