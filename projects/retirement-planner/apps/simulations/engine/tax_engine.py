"""
Tax Engine
----------
Handles tax treatment for different account types during simulation.
All rates are passed as decimals (e.g. 22.0 means 22%).
"""
from decimal import Decimal


def pre_tax_withdrawal_net(gross_amount: float, tax_rate_pct: float) -> float:
    """
    Pre-tax (traditional 401k, trad IRA, 403b, 457):
    Withdrawals are taxed as ordinary income.
    Returns net after-tax amount.
    """
    tax_rate = tax_rate_pct / 100.0
    return gross_amount * (1.0 - tax_rate)


def post_tax_withdrawal_net(gross_amount: float) -> float:
    """
    Post-tax Roth accounts: withdrawals are completely tax-free.
    """
    return gross_amount


def taxable_account_annual_tax(
    gain_amount: float,
    capital_gains_rate_pct: float,
    dividend_yield_pct: float = 2.0,
    balance: float = 0.0,
) -> float:
    """
    Taxable brokerage accounts:
    - Dividends taxed at capital gains rate annually
    - Realized gains taxed on withdrawal (simplified: we tax gains on growth)
    Returns annual tax drag amount.
    """
    rate = capital_gains_rate_pct / 100.0
    dividend_tax = balance * (dividend_yield_pct / 100.0) * rate
    gain_tax = gain_amount * rate
    return dividend_tax + gain_tax


def hsa_withdrawal_net(gross_amount: float, is_medical: bool = True) -> float:
    """
    HSA: triple tax-advantaged — contributions pre-tax, growth tax-free,
    withdrawals tax-free for qualified medical expenses.
    After 65, non-medical withdrawals taxed as ordinary income (handled like pre-tax).
    """
    if is_medical:
        return gross_amount
    # Non-medical after 65: treated like traditional IRA (simplified)
    return gross_amount * 0.80  # approximate 20% effective rate


def pension_annual_net(annual_amount: float, tax_rate_pct: float) -> float:
    """
    Pension income: taxed as ordinary income.
    """
    return annual_amount * (1.0 - tax_rate_pct / 100.0)


def ss_taxable_portion(ss_annual: float, other_income: float, filing_status: str = "single") -> float:
    """
    Calculate what portion of Social Security is subject to income tax.
    Uses the IRS combined income thresholds (simplified).

    Combined income = AGI + non-taxable interest + 50% of SS benefits.
    Returns taxable portion of SS (0, 50%, or 85% of benefit).
    """
    combined_income = other_income + (ss_annual * 0.5)

    if filing_status in ("married_jointly",):
        threshold_50 = 32_000
        threshold_85 = 44_000
    else:  # single, head_of_household, married_separately
        threshold_50 = 25_000
        threshold_85 = 34_000

    if combined_income < threshold_50:
        taxable_pct = 0.0
    elif combined_income < threshold_85:
        taxable_pct = 0.50
    else:
        taxable_pct = 0.85

    return ss_annual * taxable_pct


def rmd_required(age: int, pre_tax_balance: float) -> float:
    """
    Required Minimum Distribution for pre-tax accounts.
    RMDs apply starting age 73 (SECURE 2.0 Act).
    Uses simplified uniform lifetime table divisors.
    """
    if age < 73:
        return 0.0

    # Simplified RMD divisors from IRS Uniform Lifetime Table
    rmd_table = {
        73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9,
        78: 22.0, 79: 21.1, 80: 20.2, 81: 19.4, 82: 18.5,
        83: 17.7, 84: 16.8, 85: 16.0, 86: 15.2, 87: 14.4,
        88: 13.7, 89: 12.9, 90: 12.2, 91: 11.5, 92: 10.8,
        93: 10.1, 94: 9.5,  95: 8.9,  96: 8.4,  97: 7.8,
        98: 7.3,  99: 6.8, 100: 6.4,
    }
    divisor = rmd_table.get(age, 6.4)  # cap at age 100 divisor
    return pre_tax_balance / divisor


def effective_withdrawal_rate(account_type_flags: dict, tax_rate_pct: float, cap_gains_rate_pct: float) -> float:
    """
    Returns what fraction of a gross withdrawal the user actually keeps,
    given account type and tax rates.
    """
    if account_type_flags.get("is_pre_tax"):
        return 1.0 - (tax_rate_pct / 100.0)
    elif account_type_flags.get("is_taxable"):
        # Approximate: assume 50% of withdrawal is gain
        gain_fraction = 0.5
        return 1.0 - (gain_fraction * cap_gains_rate_pct / 100.0)
    else:
        # Roth or HSA (medical)
        return 1.0
