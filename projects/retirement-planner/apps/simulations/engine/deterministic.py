"""
Deterministic Simulation Engine
--------------------------------
Single-pass year-by-year projection using fixed return rates.
Fast (~50ms); runs synchronously in the web request.

Output schema (result_data):
{
  "schema_version": 1,
  "simulation_type": "deterministic",
  "years": [
    {
      "year": 2025,
      "age": 45,
      "spouse_age": 43,           # null if no spouse
      "phase": "accumulation",    # or "retirement" or "both_retired"
      "total_income": 150000.0,
      "total_contributions": 25000.0,
      "ss_income": 0.0,
      "pension_income": 0.0,
      "annual_spending": 80000.0,
      "withdrawal_needed": 0.0,
      "total_portfolio": 450000.0,
      "accounts": {               # balance per account id at year end
        "1": 200000.0,
        "2": 150000.0,
      },
      "black_swan_event": null,   # or {"loss_pct": 35.0, "loss_amount": 50000.0}
      "is_rmd_year": false,
      "rmd_amount": 0.0,
      "net_worth": 450000.0,
    },
    ...
  ],
  "summary": {
    "retirement_age_user": 65,
    "retirement_age_spouse": 63,
    "balance_at_user_retirement": 1200000.0,
    "final_balance": 850000.0,
    "portfolio_exhausted": false,
    "exhaustion_age": null,
    "black_swan_events": []
  }
}
"""
import copy
import random
from dataclasses import dataclass, field
from typing import List, Optional

from .tax_engine import (
    pre_tax_withdrawal_net,
    post_tax_withdrawal_net,
    rmd_required,
    ss_taxable_portion,
)
from .black_swan import (
    BlackSwanConfig,
    BlackSwanState,
    check_and_apply_black_swan,
    get_return_suppression_factor,
    advance_recoveries,
)


@dataclass
class AccountState:
    id: int
    name: str
    balance: float
    annual_contribution: float
    employer_match_annual: float
    stock_pct: float        # 0–100
    bond_pct: float         # 0–100
    is_pre_tax: bool
    is_taxable: bool
    is_hsa: bool
    is_pension: bool
    owner: str              # "self" or "spouse"
    is_active: bool
    # Pension
    expected_pension_annual: float = 0.0
    pension_start_age: Optional[int] = None


@dataclass
class SimulationInput:
    # Profile
    current_age: int
    target_retirement_age: int
    life_expectancy_age: int
    annual_income: float
    income_growth_rate_pct: float
    filing_status: str = "single"

    # Spouse
    spouse_current_age: Optional[int] = None
    spouse_retirement_age: Optional[int] = None
    spouse_life_expectancy_age: Optional[int] = None
    spouse_annual_income: float = 0.0
    spouse_income_growth_rate_pct: float = 3.0

    # SS
    ss_monthly_self: float = 0.0
    ss_claim_age_self: int = 67
    ss_cola_pct: float = 2.5
    ss_monthly_spouse: float = 0.0
    ss_claim_age_spouse: int = 67

    # Accounts
    accounts: List[AccountState] = field(default_factory=list)

    # Scenario params
    return_stocks_pct: float = 7.0
    return_bonds_pct: float = 3.5
    inflation_pct: float = 2.5
    annual_retirement_spending: float = 0.0
    spending_growth_pct: float = 2.5
    spending_strategy: str = "fixed"
    withdrawal_rate_pct: float = 4.0

    # Taxes
    tax_rate_working_pct: float = 22.0
    tax_rate_retirement_pct: float = 15.0
    cap_gains_rate_pct: float = 15.0

    # Black swan
    black_swan: Optional[BlackSwanConfig] = None


def run_deterministic(inputs: SimulationInput, rng: random.Random = None) -> dict:
    """
    Run a single deterministic simulation. Returns result_data dict.
    """
    rng = rng or random.Random()

    accounts = [copy.deepcopy(a) for a in inputs.accounts]
    bs_config = inputs.black_swan or BlackSwanConfig(enabled=False)
    bs_state = BlackSwanState()

    years_output = []
    summary = {}

    age = inputs.current_age
    spouse_age = inputs.spouse_current_age
    income_self = inputs.annual_income
    income_spouse = inputs.spouse_annual_income
    annual_spending = inputs.annual_retirement_spending  # in today's dollars

    balance_at_user_retirement = None
    portfolio_exhausted = False
    exhaustion_age = None
    current_year_index = 0  # for calendar year calculation

    import datetime
    base_year = datetime.date.today().year

    max_age = inputs.life_expectancy_age
    if inputs.spouse_life_expectancy_age:
        max_age = max(max_age, inputs.life_expectancy_age)

    while age <= max_age:
        year = base_year + current_year_index
        retired_self = age >= inputs.target_retirement_age
        retired_spouse = (
            spouse_age is not None and
            inputs.spouse_retirement_age is not None and
            spouse_age >= inputs.spouse_retirement_age
        )

        # ---- Income ----
        total_income = 0.0
        if not retired_self:
            total_income += income_self
        if spouse_age is not None and not retired_spouse:
            total_income += income_spouse

        # ---- Social Security ----
        ss_self = 0.0
        if retired_self and age >= inputs.ss_claim_age_self:
            years_since_62 = max(0, age - 62)
            cola_factor = (1 + inputs.ss_cola_pct / 100) ** years_since_62
            ss_self = inputs.ss_monthly_self * 12 * cola_factor

        ss_spouse = 0.0
        if (spouse_age is not None and retired_spouse and
                inputs.ss_monthly_spouse > 0 and
                spouse_age >= inputs.ss_claim_age_spouse):
            years_since_62 = max(0, spouse_age - 62)
            cola_factor = (1 + inputs.ss_cola_pct / 100) ** years_since_62
            ss_spouse = inputs.ss_monthly_spouse * 12 * cola_factor

        ss_total = ss_self + ss_spouse

        # ---- Pension income ----
        pension_total = 0.0
        for acct in accounts:
            if acct.is_pension and acct.pension_start_age and age >= acct.pension_start_age:
                pension_total += acct.expected_pension_annual

        # ---- Contributions (accumulation phase) ----
        total_contributions = 0.0
        for acct in accounts:
            if acct.is_active and not acct.is_pension:
                owner_retired = retired_self if acct.owner == "self" else retired_spouse
                if not owner_retired:
                    contrib = acct.annual_contribution + acct.employer_match_annual
                    acct.balance += contrib
                    total_contributions += contrib

        # ---- Grow accounts ----
        total_portfolio_before = sum(a.balance for a in accounts if not a.is_pension)

        # Black swan: apply event and get suppression factor
        total_portfolio_before, bs_state, bs_event = check_and_apply_black_swan(
            year=year, age=age,
            portfolio_value=total_portfolio_before,
            config=bs_config, state=bs_state, rng=rng,
        )
        suppression = get_return_suppression_factor(bs_state)
        bs_state = advance_recoveries(bs_state)

        # Apply suppression proportionally to each account's balance
        if sum(a.balance for a in accounts if not a.is_pension) > 0:
            ratio = total_portfolio_before / sum(a.balance for a in accounts if not a.is_pension)
            for acct in accounts:
                if not acct.is_pension:
                    acct.balance *= ratio

        for acct in accounts:
            if acct.is_pension:
                continue
            stock_return = (inputs.return_stocks_pct / 100) * suppression
            bond_return = (inputs.return_bonds_pct / 100) * suppression
            blended_return = (acct.stock_pct / 100) * stock_return + (acct.bond_pct / 100) * bond_return
            acct.balance *= (1 + blended_return)

        # ---- RMD ----
        rmd_amount = 0.0
        if retired_self and age >= 73:
            pre_tax_total = sum(a.balance for a in accounts if a.is_pre_tax and a.owner == "self")
            rmd_amount = rmd_required(age, pre_tax_total)
            # Force RMD withdrawal from pre-tax accounts
            if rmd_amount > 0:
                _withdraw_from_accounts(accounts, rmd_amount, "pre_tax_first", owner="self")

        # ---- Spending & Withdrawals ----
        inflation_factor = (1 + inputs.inflation_pct / 100) ** current_year_index

        if retired_self or (retired_spouse and spouse_age is not None):
            # Inflation-adjusted spending target
            if inputs.spending_strategy == "fixed":
                target_spending = annual_spending * inflation_factor
            elif inputs.spending_strategy == "percent_portfolio":
                total_port = sum(a.balance for a in accounts if not a.is_pension)
                target_spending = total_port * (inputs.withdrawal_rate_pct / 100)
            else:  # guardrails
                target_spending = annual_spending * inflation_factor
                total_port = sum(a.balance for a in accounts if not a.is_pension)
                peak = max(target_spending, total_port * 0.04)  # simplified
                if total_port < peak * 0.80:
                    target_spending *= 0.90  # reduce 10% if down 20%

            gap = max(0.0, target_spending - ss_total - pension_total)
            if gap > 0:
                withdrawn = _withdraw_from_accounts(accounts, gap, "tax_efficient", owner="self")
                if withdrawn < gap:
                    portfolio_exhausted = True
                    exhaustion_age = age
        else:
            target_spending = 0.0
            gap = 0.0

        # ---- Year-end snapshot ----
        total_portfolio = sum(a.balance for a in accounts if not a.is_pension)
        if balance_at_user_retirement is None and retired_self:
            balance_at_user_retirement = total_portfolio

        if portfolio_exhausted and exhaustion_age == age:
            pass  # already recorded

        year_row = {
            "year": year,
            "age": age,
            "spouse_age": spouse_age,
            "phase": _phase(retired_self, retired_spouse, spouse_age),
            "total_income": round(total_income, 2),
            "total_contributions": round(total_contributions, 2),
            "ss_income": round(ss_total, 2),
            "pension_income": round(pension_total, 2),
            "annual_spending": round(target_spending, 2),
            "withdrawal_needed": round(gap, 2),
            "total_portfolio": round(total_portfolio, 2),
            "accounts": {str(a.id): round(a.balance, 2) for a in accounts},
            "black_swan_event": bs_event,
            "is_rmd_year": rmd_amount > 0,
            "rmd_amount": round(rmd_amount, 2),
            "net_worth": round(total_portfolio, 2),
        }
        years_output.append(year_row)

        # ---- Advance ----
        age += 1
        if spouse_age is not None:
            spouse_age += 1
        if not retired_self:
            income_self *= (1 + inputs.income_growth_rate_pct / 100)
        if spouse_age is not None and not retired_spouse:
            income_spouse *= (1 + inputs.spouse_income_growth_rate_pct / 100)
        current_year_index += 1

    final_balance = years_output[-1]["total_portfolio"] if years_output else 0.0

    summary = {
        "retirement_age_user": inputs.target_retirement_age,
        "retirement_age_spouse": inputs.spouse_retirement_age,
        "balance_at_user_retirement": round(balance_at_user_retirement or 0.0, 2),
        "final_balance": round(final_balance, 2),
        "portfolio_exhausted": portfolio_exhausted,
        "exhaustion_age": exhaustion_age,
        "black_swan_events": bs_state.events_triggered,
    }

    return {
        "schema_version": 1,
        "simulation_type": "deterministic",
        "years": years_output,
        "summary": summary,
    }


def _phase(retired_self: bool, retired_spouse: bool, spouse_age) -> str:
    if spouse_age is None:
        return "retirement" if retired_self else "accumulation"
    if retired_self and retired_spouse:
        return "both_retired"
    if retired_self or retired_spouse:
        return "partial_retirement"
    return "accumulation"


def _withdraw_from_accounts(
    accounts: List[AccountState],
    amount_needed: float,
    strategy: str = "tax_efficient",
    owner: str = "self",
) -> float:
    """
    Withdraw `amount_needed` from accounts using the given strategy.
    Tax-efficient order: taxable → pre-tax → Roth
    Returns total amount actually withdrawn.
    """
    remaining = amount_needed
    withdrawn = 0.0

    if strategy == "tax_efficient":
        order = ["taxable", "pre_tax", "roth"]
    elif strategy == "pre_tax_first":
        order = ["pre_tax", "taxable", "roth"]
    else:
        order = ["taxable", "pre_tax", "roth"]

    for acct_type in order:
        for acct in accounts:
            if remaining <= 0:
                break
            if acct.owner != owner:
                continue
            if acct.is_pension:
                continue
            matches = (
                (acct_type == "taxable" and acct.is_taxable) or
                (acct_type == "pre_tax" and acct.is_pre_tax) or
                (acct_type == "roth" and not acct.is_pre_tax and not acct.is_taxable and not acct.is_hsa and not acct.is_pension)
            )
            if not matches:
                continue
            take = min(remaining, acct.balance)
            acct.balance -= take
            remaining -= take
            withdrawn += take

    return withdrawn
