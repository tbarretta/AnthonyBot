from django import forms
from .models import Scenario, SimulationType, SpendingStrategy


class ScenarioForm(forms.ModelForm):
    class Meta:
        model = Scenario
        fields = [
            "name", "description", "simulation_type",
            "expected_annual_return_stocks", "expected_annual_return_bonds", "inflation_rate",
            "annual_retirement_spending", "spending_growth_rate", "spending_strategy", "withdrawal_rate_pct",
            "mc_iterations", "mc_confidence_level", "mc_return_std_dev_stocks", "mc_return_std_dev_bonds",
            "black_swan_enabled", "black_swan_annual_probability",
            "black_swan_min_loss_pct", "black_swan_max_loss_pct", "black_swan_recovery_years",
            "effective_tax_rate_working", "effective_tax_rate_retirement", "capital_gains_rate",
            "user_life_expectancy_age", "spouse_life_expectancy_age",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "simulation_type": forms.RadioSelect(),
            "spending_strategy": forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop("profile", None)
        super().__init__(*args, **kwargs)
        # Pre-fill life expectancy from profile if not set
        if self.profile and not self.instance.pk:
            self.fields["user_life_expectancy_age"].initial = self.profile.life_expectancy_age
            if self.profile.has_spouse:
                self.fields["spouse_life_expectancy_age"].initial = self.profile.spouse.life_expectancy_age
