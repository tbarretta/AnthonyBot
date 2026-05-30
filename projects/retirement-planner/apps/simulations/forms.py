from django import forms
from .models import Scenario, SimulationType, SpendingStrategy


class ScenarioForm(forms.ModelForm):
    class Meta:
        model = Scenario
        fields = [
            "name", "description",
            # simulation_type is fixed to deterministic — Monte Carlo coming later
            "expected_annual_return_stocks", "expected_annual_return_bonds", "inflation_rate",
            "annual_retirement_spending", "spending_growth_rate", "spending_strategy", "withdrawal_rate_pct",
            # mc_* fields omitted from UI until Monte Carlo is enabled
            "black_swan_enabled", "black_swan_annual_probability",
            "black_swan_min_loss_pct", "black_swan_max_loss_pct", "black_swan_recovery_years",
            # Social Security — primary user
            "ss_monthly_self_at_62", "ss_monthly_self_at_67", "ss_monthly_self_at_70", "ss_claim_age_self",
            # Social Security — spouse
            "ss_monthly_spouse_at_62", "ss_monthly_spouse_at_67", "ss_monthly_spouse_at_70", "ss_claim_age_spouse",
            # SS shared
            "ss_cola_rate",
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

        # Hide spouse SS fields if no spouse on profile
        if self.profile and not self.profile.has_spouse:
            for field in ["ss_monthly_spouse_at_62", "ss_monthly_spouse_at_67",
                          "ss_monthly_spouse_at_70", "ss_claim_age_spouse"]:
                self.fields[field].widget = forms.HiddenInput()
                self.fields[field].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Always deterministic until Monte Carlo is re-enabled
        instance.simulation_type = "deterministic"
        if commit:
            instance.save()
        return instance
