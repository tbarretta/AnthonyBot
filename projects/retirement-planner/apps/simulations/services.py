"""
Simulation Services
-------------------
Thin service layer that bridges Django models → simulation engine.
Views and API endpoints call these functions; they never call the engine directly.
"""
from django.utils import timezone

from apps.investments.models import InvestmentAccount
from apps.profiles.models import SocialSecurityEstimate
from .models import Scenario, SimulationResult, SimulationStatus
from .engine.deterministic import SimulationInput, AccountState, BlackSwanConfig, run_deterministic


def build_simulation_input(scenario: Scenario) -> SimulationInput:
    """
    Convert Django model data into a SimulationInput dataclass
    for the engine to consume.
    """
    profile = scenario.user_profile
    accounts_qs = InvestmentAccount.objects.filter(user_profile=profile)

    # SS estimates
    ss_self_obj = SocialSecurityEstimate.objects.filter(user_profile=profile, owner="self").first()
    ss_spouse_obj = SocialSecurityEstimate.objects.filter(user_profile=profile, owner="spouse").first()

    ss_monthly_self = float(ss_self_obj.monthly_benefit_at_claim_age()) if ss_self_obj else 0.0
    ss_claim_age_self = ss_self_obj.claim_age if ss_self_obj else 67
    ss_cola = float(ss_self_obj.cola_rate) if ss_self_obj else 2.5

    ss_monthly_spouse = float(ss_spouse_obj.monthly_benefit_at_claim_age()) if ss_spouse_obj else 0.0
    ss_claim_age_spouse = ss_spouse_obj.claim_age if ss_spouse_obj else 67

    # Spouse
    spouse_current_age = None
    spouse_retirement_age = None
    spouse_life_expectancy = None
    spouse_annual_income = 0.0
    spouse_income_growth = 3.0
    if profile.has_spouse:
        sp = profile.spouse
        spouse_current_age = sp.current_age
        spouse_retirement_age = sp.target_retirement_age
        spouse_life_expectancy = scenario.spouse_life_expectancy_age or sp.life_expectancy_age
        spouse_annual_income = float(sp.annual_income)
        spouse_income_growth = float(sp.income_growth_rate)

    # Accounts → AccountState
    account_states = []
    for acct in accounts_qs:
        account_states.append(AccountState(
            id=acct.id,
            name=acct.name,
            balance=float(acct.current_balance),
            annual_contribution=float(acct.annual_contribution),
            employer_match_annual=acct.effective_employer_match_annual,
            stock_pct=float(acct.asset_allocation_stocks),
            bond_pct=float(acct.asset_allocation_bonds),
            is_pre_tax=acct.is_pre_tax,
            is_taxable=acct.is_taxable,
            is_hsa=acct.is_hsa,
            is_pension=acct.is_pension,
            owner=acct.owner,
            is_active=acct.is_active,
            expected_pension_annual=float(acct.expected_pension_annual),
            pension_start_age=acct.pension_start_age,
        ))

    black_swan = BlackSwanConfig(
        enabled=scenario.black_swan_enabled,
        annual_probability_pct=float(scenario.black_swan_annual_probability),
        min_loss_pct=float(scenario.black_swan_min_loss_pct),
        max_loss_pct=float(scenario.black_swan_max_loss_pct),
        recovery_years=scenario.black_swan_recovery_years,
    )

    return SimulationInput(
        current_age=profile.current_age,
        target_retirement_age=scenario.user_life_expectancy_age or profile.target_retirement_age,
        life_expectancy_age=scenario.user_life_expectancy_age or profile.life_expectancy_age,
        annual_income=float(profile.annual_income),
        income_growth_rate_pct=float(profile.income_growth_rate),
        filing_status=profile.filing_status,

        spouse_current_age=spouse_current_age,
        spouse_retirement_age=spouse_retirement_age,
        spouse_life_expectancy_age=spouse_life_expectancy,
        spouse_annual_income=spouse_annual_income,
        spouse_income_growth_rate_pct=spouse_income_growth,

        ss_monthly_self=ss_monthly_self,
        ss_claim_age_self=ss_claim_age_self,
        ss_cola_pct=ss_cola,
        ss_monthly_spouse=ss_monthly_spouse,
        ss_claim_age_spouse=ss_claim_age_spouse,

        accounts=account_states,

        return_stocks_pct=float(scenario.expected_annual_return_stocks),
        return_bonds_pct=float(scenario.expected_annual_return_bonds),
        inflation_pct=float(scenario.inflation_rate),
        annual_retirement_spending=float(scenario.annual_retirement_spending),
        spending_growth_pct=float(scenario.spending_growth_rate),
        spending_strategy=scenario.spending_strategy,
        withdrawal_rate_pct=float(scenario.withdrawal_rate_pct),

        tax_rate_working_pct=float(scenario.effective_tax_rate_working),
        tax_rate_retirement_pct=float(scenario.effective_tax_rate_retirement),
        cap_gains_rate_pct=float(scenario.capital_gains_rate),

        black_swan=black_swan,
    )


def run_deterministic_sync(scenario: Scenario) -> SimulationResult:
    """
    Run a deterministic simulation synchronously.
    Returns a saved SimulationResult.
    """
    result = SimulationResult.objects.create(
        scenario=scenario,
        status=SimulationStatus.RUNNING,
        started_at=timezone.now(),
    )

    try:
        inputs = build_simulation_input(scenario)
        data = run_deterministic(inputs)

        summary = data["summary"]
        years = data["years"]

        result.status = SimulationStatus.COMPLETE
        result.result_data = data
        result.deterministic_final_balance = summary["final_balance"]
        result.portfolio_exhaustion_age = summary.get("exhaustion_age")
        result.median_balance_at_retirement = summary["balance_at_user_retirement"]
        result.median_balance_at_end = summary["final_balance"]
        result.completed_at = timezone.now()
        result.save()

    except Exception as exc:
        result.status = SimulationStatus.FAILED
        result.error_message = str(exc)
        result.completed_at = timezone.now()
        result.save()
        raise

    return result
