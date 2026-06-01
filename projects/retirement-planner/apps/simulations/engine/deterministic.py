"""
Deterministic Simulation Engine
--------------------------------
Single-pass year-by-year projection using fixed return rates.
Fast (~50ms); runs synchronously in the web request.

Output schema (result_data):
{
  "schema_version": 2,
  "simulation_type": "deterministic",
  "years": [
    {
      "year": 2025,
      "age": 45,
      "spouse_age": 43,           # null if no spouse
      "phase": "accumulation",    # or "retirement" or "both_retired"
      "total_income": 150000.0,
      "total_contributions": 25000.0,
      "income_sources": [         # per-source breakdown for this year
        {
          "id": 1,
          "name": "Tom's SS",
          "source_type": "social_security",
          "annual_income": 0.0,
          "is_active": false,
          "years_until_start": 22
        },
        ...
      ],
      "total_guaranteed_income": 0.0,   # sum of active income sources
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
    owner: str              # "self" or "spouse"
    is_active: bool


@dataclass
class IncomeSourceInput:
    """
    A single guaranteed / recurring income stream for the engine.
    Services layer pre-populates all fields; the engine does not touch models.
    """
    id: int
    name: str
    source_type: str          # matches IncomeSourceType values
    owner: str                # "self" or "spouse"

    # SS-specific (pre-interpolated by services.py)
    ss_monthly_at_claim_age: float = 0.0
    ss_cola_rate: float = 2.5
    ss_claim_age: int = 67

    # Non-SS
    annual_amount: float = 0.0
    start_age: int = 65
    end_age: Optional[int] = None

    # Growth / inflation
    is_inflation_adjusted: bool = False
    inflation_rate_override: Optional[float] = None

    # Tax treatment
    is_taxable: bool = True
    tax_rate_override: Optional[float] = None

    # Pension survivor benefit
    survivor_benefit_pct: Optional[float] = None


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

    # Income sources (replaces SS + pension fields)
    income_sources: List[IncomeSourceInput] = field(default_factory=list)

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
    guardrails_enabled: bool = False

    # Taxes
    tax_rate_working_pct: float = 22.0
    tax_rate_retirement_pct: float = 15.0
    cap_gains_rate_pct: float = 15.0

    # Black swan
    black_swan: Optional[BlackSwanConfig] = None


def _compute_income_source_annual(
    src: IncomeSourceInput,
    age: int,
    spouse_age: Optional[int],
    current_year_index: int,
    inflation_pct: float,
    tax_rate_retirement_pct: float,
    retired_self: bool,
    retired_spouse: bool,
) -> tuple[float, bool, int]:
    """
    Compute annual income from a single IncomeSourceInput for the given year.

    Returns:
        (annual_income, is_active, years_until_start)
    """
    # Determine owner's current age
    owner_age = age if src.owner == "self" else (spouse_age if spouse_age is not None else None)
    owner_retired = retired_self if src.owner == "self" else retired_spouse

    if owner_age is None:
        # No spouse in plan; skip spouse-owned sources
        return 0.0, False, 0

    if src.source_type == "social_security":
        # SS: active when owner's age >= ss_claim_age
        if owner_age >= src.ss_claim_age:
            # COLA factor from claim age onwards
            years_collecting = owner_age - src.ss_claim_age
            cola_factor = (1 + src.ss_cola_rate / 100) ** years_collecting
            annual = src.ss_monthly_at_claim_age * 12 * cola_factor
            return annual, True, 0
        else:
            years_until = src.ss_claim_age - owner_age
            return 0.0, False, years_until
    else:
        # Non-SS: active when owner's age >= start_age AND (no end_age or age <= end_age)
        started = owner_age >= src.start_age
        not_ended = src.end_age is None or owner_age <= src.end_age
        if started and not_ended:
            base = src.annual_amount
            if src.is_inflation_adjusted:
                rate = src.inflation_rate_override if src.inflation_rate_override is not None else inflation_pct
                years_inflated = owner_age - src.start_age
                base = base * (1 + rate / 100) ** years_inflated
            return base, True, 0
        else:
            years_until = max(0, src.start_age - owner_age) if not started else 0
            return 0.0, False, years_until


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

        # ---- Employment Income ----
        total_income = 0.0
        if not retired_self:
            total_income += income_self
        if spouse_age is not None and not retired_spouse:
            total_income += income_spouse

        # ---- Guaranteed Income Sources ----
        income_source_rows = []
        total_guaranteed_income = 0.0

        for src in inputs.income_sources:
            annual_income, is_active, years_until_start = _compute_income_source_annual(
                src=src,
                age=age,
                spouse_age=spouse_age,
                current_year_index=current_year_index,
                inflation_pct=inputs.inflation_pct,
                tax_rate_retirement_pct=inputs.tax_rate_retirement_pct,
                retired_self=retired_self,
                retired_spouse=retired_spouse,
            )
            if is_active:
                total_guaranteed_income += annual_income

            row = {
                "id": src.id,
                "name": src.name,
                "source_type": src.source_type,
                "annual_income": round(annual_income, 2),
                "is_active": is_active,
            }
            if not is_active:
                row["years_until_start"] = years_until_start
            income_source_rows.append(row)

        # Legacy aliases for backward compat with existing result templates
        ss_total = sum(
            r["annual_income"] for r in income_source_rows
            if r["source_type"] == "social_security" and r["is_active"]
        )
        pension_total = sum(
            r["annual_income"] for r in income_source_rows
            if r["source_type"] == "pension" and r["is_active"]
        )

        # ---- Contributions (accumulation phase) ----
        total_contributions = 0.0
        for acct in accounts:
            if acct.is_active:
                owner_retired = retired_self if acct.owner == "self" else retired_spouse
                if not owner_retired:
                    contrib = acct.annual_contribution + acct.employer_match_annual
                    acct.balance += contrib
                    total_contributions += contrib

        # ---- Grow accounts ----
        total_portfolio_before = sum(a.balance for a in accounts)

        # Black swan: apply event and get suppression factor
        total_portfolio_before, bs_state, bs_event = check_and_apply_black_swan(
            year=year, age=age,
            portfolio_value=total_portfolio_before,
            config=bs_config, state=bs_state, rng=rng,
        )
        suppression = get_return_suppression_factor(bs_state)
        bs_state = advance_recoveries(bs_state)

        # Apply suppression proportionally to each account's balance
        acct_total = sum(a.balance for a in accounts)
        if acct_total > 0:
            ratio = total_portfolio_before / acct_total
            for acct in accounts:
                acct.balance *= ratio

        # Growth applies from year 2 onwards; year 1 reflects current balances + contributions only
        if current_year_index > 0:
            for acct in accounts:
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

        if retired_self:  # spending phase begins when the primary user retires, not the spouse
            # Base spending target
            if inputs.spending_strategy == "percent_portfolio":
                total_port = sum(a.balance for a in accounts)
                target_spending = total_port * (inputs.withdrawal_rate_pct / 100)
            else:  # fixed (inflation-adjusted)
                target_spending = annual_spending * inflation_factor

            # Guardrails modifier: reduce 10% if portfolio > 20% below its peak
            if inputs.guardrails_enabled:
                total_port = sum(a.balance for a in accounts)
                peak = max(target_spending, total_port * 0.04)  # simplified floor
                if total_port < peak * 0.80:
                    target_spending *= 0.90

            # net_gap = after-tax dollars still needed from the portfolio
            net_gap = max(0.0, target_spending - total_guaranteed_income)
            gross_gap = 0.0
            taxes_paid = 0.0
            if net_gap > 0:
                # Gross up: withdraw enough to cover taxes and still net net_gap
                gross_gap = _compute_gross_withdrawal_needed(
                    net_needed=net_gap,
                    accounts=accounts,
                    owner="self",
                    tax_rate_retirement_pct=inputs.tax_rate_retirement_pct,
                    cap_gains_rate_pct=inputs.cap_gains_rate_pct,
                )
                taxes_paid = gross_gap - net_gap
                withdrawn = _withdraw_from_accounts(accounts, gross_gap, "tax_efficient", owner="self")
                if withdrawn < gross_gap - 0.01 and not portfolio_exhausted:  # first year portfolio hits $0
                    portfolio_exhausted = True
                    exhaustion_age = age
            gap = net_gap  # keep as net spending gap for display
        else:
            target_spending = 0.0
            gap = 0.0
            gross_gap = 0.0
            taxes_paid = 0.0

        # ---- Year-end snapshot ----
        total_portfolio = sum(a.balance for a in accounts)
        if balance_at_user_retirement is None and retired_self:
            balance_at_user_retirement = total_portfolio

        year_row = {
            "year": year,
            "age": age,
            "spouse_age": spouse_age,
            "phase": _phase(retired_self, retired_spouse, spouse_age),
            "total_income": round(total_income, 2),
            "total_contributions": round(total_contributions, 2),
            # Guaranteed income breakdown
            "income_sources": income_source_rows,
            "total_guaranteed_income": round(total_guaranteed_income, 2),
            # Legacy aliases (kept for template compatibility)
            "ss_income": round(ss_total, 2),
            "pension_income": round(pension_total, 2),
            "annual_spending": round(target_spending, 2),   # after-tax spending target
            "withdrawal_needed": round(gross_gap, 2),          # gross pulled from portfolio
            "taxes_paid": round(taxes_paid, 2),                # estimated tax on withdrawals
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
        "schema_version": 2,
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


def _compute_gross_withdrawal_needed(
    net_needed: float,
    accounts: List[AccountState],
    owner: str,
    tax_rate_retirement_pct: float,
    cap_gains_rate_pct: float,
    gain_fraction: float = 0.5,
) -> float:
    """
    Given the net (after-tax) dollars needed from the portfolio, compute the
    gross withdrawal required, accounting for the tax treatment of each account
    type in tax-efficient withdrawal order (taxable → pre-tax → Roth).

    - Pre-tax (trad 401k/IRA): taxed at effective_tax_rate_retirement
    - Taxable brokerage: cap gains on estimated gain_fraction of withdrawal
    - Roth / HSA (medical): tax-free, keep 100%
    """
    tax_rate = tax_rate_retirement_pct / 100.0
    cap_gains_rate = cap_gains_rate_pct / 100.0

    remaining_net = net_needed
    gross_total = 0.0

    for acct_type in ["taxable", "pre_tax", "roth"]:
        if remaining_net <= 0:
            break
        for acct in accounts:
            if remaining_net <= 0:
                break
            if acct.owner != owner or acct.balance <= 0:
                continue
            matches = (
                (acct_type == "taxable" and acct.is_taxable) or
                (acct_type == "pre_tax" and acct.is_pre_tax) or
                (acct_type == "roth" and not acct.is_pre_tax and not acct.is_taxable and not acct.is_hsa)
            )
            if not matches:
                continue

            if acct.is_pre_tax:
                keep_rate = 1.0 - tax_rate
            elif acct.is_taxable:
                keep_rate = 1.0 - (gain_fraction * cap_gains_rate)
            else:  # Roth / HSA
                keep_rate = 1.0

            keep_rate = max(keep_rate, 0.01)  # safety floor
            max_net_from_acct = acct.balance * keep_rate
            net_from_acct = min(remaining_net, max_net_from_acct)
            gross_total += net_from_acct / keep_rate
            remaining_net -= net_from_acct

    # If accounts are exhausted before covering net_needed, add remainder 1:1
    # (the depletion check in the caller will flag this run)
    if remaining_net > 0:
        gross_total += remaining_net

    return gross_total


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
            matches = (
                (acct_type == "taxable" and acct.is_taxable) or
                (acct_type == "pre_tax" and acct.is_pre_tax) or
                (acct_type == "roth" and not acct.is_pre_tax and not acct.is_taxable and not acct.is_hsa)
            )
            if not matches:
                continue
            take = min(remaining, acct.balance)
            acct.balance -= take
            remaining -= take
            withdrawn += take

    return withdrawn
