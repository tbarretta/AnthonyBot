from django.db import models
from apps.profiles.models import UserProfile


class SimulationType(models.TextChoices):
    DETERMINISTIC = "deterministic", "Deterministic"
    MONTE_CARLO = "monte_carlo", "Monte Carlo"


class SpendingStrategy(models.TextChoices):
    FIXED = "fixed", "Fixed (inflation-adjusted)"
    PERCENT_OF_PORTFOLIO = "percent_portfolio", "% of Portfolio (e.g. 4% rule)"


class SimulationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETE = "complete", "Complete"
    FAILED = "failed", "Failed"


class Scenario(models.Model):
    """
    A named simulation configuration. Users can create multiple scenarios
    to compare outcomes (e.g. "Retire at 60 aggressive" vs "Retire at 67 moderate").
    """
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="scenarios",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    simulation_type = models.CharField(
        max_length=20,
        choices=SimulationType.choices,
        default=SimulationType.DETERMINISTIC,
    )

    # ---- Retirement Ages ----
    retirement_age_self = models.PositiveSmallIntegerField(
        default=65,
        help_text="Age at which you plan to retire (stops contributions, starts withdrawals)"
    )
    retirement_age_spouse = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Age at which spouse plans to retire"
    )

    # ---- Return Assumptions ----
    expected_annual_return_stocks = models.DecimalField(
        max_digits=5, decimal_places=2, default=7.0,
        help_text="Expected annual stock return %, e.g. 7.0"
    )
    expected_annual_return_bonds = models.DecimalField(
        max_digits=5, decimal_places=2, default=3.5,
        help_text="Expected annual bond return %, e.g. 3.5"
    )
    inflation_rate = models.DecimalField(
        max_digits=4, decimal_places=2, default=2.5,
        help_text="Annual inflation rate %, e.g. 2.5"
    )

    # ---- Retirement Spending ----
    annual_retirement_spending = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Target annual spending in retirement (today's dollars)"
    )
    spending_growth_rate = models.DecimalField(
        max_digits=4, decimal_places=2, default=2.5,
        help_text="Annual spending growth % (typically = inflation)"
    )
    spending_strategy = models.CharField(
        max_length=20,
        choices=SpendingStrategy.choices,
        default=SpendingStrategy.FIXED,
    )
    guardrails_enabled = models.BooleanField(
        default=False,
        help_text="Reduce spending by 10% in any year the portfolio drops >20% below its peak",
    )
    # For percent_portfolio strategy
    withdrawal_rate_pct = models.DecimalField(
        max_digits=4, decimal_places=2, default=4.0,
        help_text="Withdrawal rate % for percent-of-portfolio strategy"
    )

    # ---- Monte Carlo Parameters ----
    mc_iterations = models.PositiveIntegerField(
        default=1000,
        help_text="Number of Monte Carlo simulation runs"
    )
    mc_confidence_level = models.PositiveSmallIntegerField(
        default=85,
        help_text="Target confidence level % (e.g. 85 = 85% of runs succeed)"
    )
    mc_return_std_dev_stocks = models.DecimalField(
        max_digits=5, decimal_places=2, default=15.0,
        help_text="Annual stock return volatility (std dev) %, e.g. 15.0"
    )
    mc_return_std_dev_bonds = models.DecimalField(
        max_digits=5, decimal_places=2, default=5.0,
        help_text="Annual bond return volatility (std dev) %, e.g. 5.0"
    )

    # ---- Black Swan ----
    black_swan_enabled = models.BooleanField(default=False)
    black_swan_annual_probability = models.DecimalField(
        max_digits=5, decimal_places=2, default=3.0,
        help_text="Annual probability of a black swan event occurring, e.g. 3.0%"
    )
    black_swan_min_loss_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=20.0,
        help_text="Minimum portfolio loss % in a black swan event"
    )
    black_swan_max_loss_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=50.0,
        help_text="Maximum portfolio loss % in a black swan event"
    )
    black_swan_recovery_years = models.PositiveSmallIntegerField(
        default=3,
        help_text="Average years for portfolio to recover post-event"
    )

    # ---- Social Security Claim Strategy ----
    # SS monthly benefit amounts (at 62/67/70) and COLA are now stored on IncomeSource.
    # The Scenario only retains the claiming age (the simulation variable).
    ss_claim_age_self = models.PositiveSmallIntegerField(
        default=67,
        help_text="Age at which you intend to claim SS benefits (62–70)"
    )
    ss_claim_age_spouse = models.PositiveSmallIntegerField(
        default=67,
        help_text="Age at which spouse intends to claim SS benefits (62–70)"
    )

    # ---- Tax Assumptions ----
    effective_tax_rate_working = models.DecimalField(
        max_digits=5, decimal_places=2, default=22.0,
        help_text="Effective income tax rate % while working"
    )
    effective_tax_rate_retirement = models.DecimalField(
        max_digits=5, decimal_places=2, default=15.0,
        help_text="Effective tax rate % on pre-tax withdrawals in retirement"
    )
    capital_gains_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=15.0,
        help_text="Long-term capital gains tax rate % for taxable accounts"
    )

    # ---- Longevity Overrides (can override profile defaults) ----
    user_life_expectancy_age = models.PositiveSmallIntegerField(null=True, blank=True)
    spouse_life_expectancy_age = models.PositiveSmallIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Scenario"

    def __str__(self):
        return f"{self.name} ({self.get_simulation_type_display()})"

    @property
    def latest_result(self):
        return self.results.filter(status=SimulationStatus.COMPLETE).order_by("-completed_at").first()


class SimulationResult(models.Model):
    """
    Stored output of a simulation run. Heavy data lives in result_data (JSON).
    Summary stats are indexed columns for quick list display.
    """
    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        related_name="results",
    )
    status = models.CharField(
        max_length=20,
        choices=SimulationStatus.choices,
        default=SimulationStatus.PENDING,
    )
    error_message = models.TextField(blank=True)

    # ---- Summary Stats (indexed for quick access) ----
    # Monte Carlo
    success_probability = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="% of MC runs that don't exhaust the portfolio"
    )
    # Both
    median_balance_at_retirement = models.DecimalField(
        max_digits=16, decimal_places=2, null=True, blank=True
    )
    median_balance_at_end = models.DecimalField(
        max_digits=16, decimal_places=2, null=True, blank=True
    )
    # Deterministic only
    deterministic_final_balance = models.DecimalField(
        max_digits=16, decimal_places=2, null=True, blank=True
    )
    # Year portfolio hits zero (deterministic)
    portfolio_exhaustion_age = models.PositiveSmallIntegerField(null=True, blank=True)

    # ---- Full result payload ----
    # Schema: { "schema_version": 1, "years": [...], "percentiles": {...}, ... }
    result_data = models.JSONField(default=dict)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-completed_at"]
        verbose_name = "Simulation Result"

    def __str__(self):
        return f"Result for '{self.scenario.name}' — {self.get_status_display()}"
