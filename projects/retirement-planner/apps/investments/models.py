from django.db import models
from apps.profiles.models import UserProfile


class AccountType(models.TextChoices):
    K401 = "401k", "401(k) — Pre-Tax"
    ROTH_401K = "roth_401k", "Roth 401(k) — Post-Tax"
    TRADITIONAL_IRA = "traditional_ira", "Traditional IRA — Pre-Tax"
    ROTH_IRA = "roth_ira", "Roth IRA — Post-Tax"
    K403B = "403b", "403(b) — Pre-Tax"
    K457 = "457", "457(b) — Pre-Tax"
    TAXABLE = "taxable", "Taxable Brokerage"
    HSA = "hsa", "HSA — Triple Tax-Advantaged"
    OTHER_PRETAX = "other_pretax", "Other Pre-Tax"
    OTHER_POSTTAX = "other_posttax", "Other Post-Tax"


# Account type → pre-tax classification
PRE_TAX_TYPES = {
    AccountType.K401,
    AccountType.TRADITIONAL_IRA,
    AccountType.K403B,
    AccountType.K457,
    AccountType.OTHER_PRETAX,
}

POST_TAX_TYPES = {
    AccountType.ROTH_401K,
    AccountType.ROTH_IRA,
    AccountType.OTHER_POSTTAX,
}

TAXABLE_TYPES = {
    AccountType.TAXABLE,
}

HSA_TYPES = {
    AccountType.HSA,
}


class AccountOwner(models.TextChoices):
    SELF = "self", "Primary User"
    SPOUSE = "spouse", "Spouse"


class InvestmentAccount(models.Model):
    """
    A single investment account (401k, Roth IRA, taxable, etc.).
    Pre-tax vs post-tax drives tax treatment in the simulation engine.
    Pension income is now modeled as an IncomeSource, not an InvestmentAccount.
    """
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="investment_accounts",
    )
    owner = models.CharField(max_length=10, choices=AccountOwner.choices, default=AccountOwner.SELF)

    name = models.CharField(max_length=200, help_text="e.g. 'Tom's 401k at Fidelity'")
    account_type = models.CharField(max_length=20, choices=AccountType.choices)

    # Tax classification (auto-set from account_type, editable for 'other' types)
    is_pre_tax = models.BooleanField(
        default=True,
        help_text="Pre-tax = contributions reduce taxable income; withdrawals taxed as ordinary income"
    )
    is_taxable = models.BooleanField(
        default=False,
        help_text="Taxable brokerage: contributions post-tax, gains taxed annually"
    )
    is_hsa = models.BooleanField(default=False)

    # Balances & Contributions
    current_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    annual_contribution = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Your annual contribution (pre-tax dollar amount)"
    )

    # Employer Match (applies to 401k-type accounts)
    employer_match_pct = models.PositiveSmallIntegerField(
        default=0,
        help_text="Employer matches this % of your contribution, e.g. 100 = dollar for dollar, 50 = 50 cents per dollar"
    )

    # Asset Allocation
    asset_allocation_stocks = models.DecimalField(
        max_digits=5, decimal_places=2, default=80,
        help_text="% allocated to equities (0–100)"
    )
    asset_allocation_bonds = models.DecimalField(
        max_digits=5, decimal_places=2, default=20,
        help_text="% allocated to bonds/fixed income (0–100)"
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="False = stopped contributing (old job); balance still grows"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["owner", "account_type", "name"]
        verbose_name = "Investment Account"

    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()})"

    def save(self, *args, **kwargs):
        """Auto-set tax classification flags from account_type."""
        self.is_pre_tax = self.account_type in PRE_TAX_TYPES
        self.is_taxable = self.account_type in TAXABLE_TYPES
        self.is_hsa = self.account_type in HSA_TYPES
        # Post-tax (Roth): not pre-tax, not taxable, not hsa
        super().save(*args, **kwargs)

    @property
    def tax_label(self):
        if self.is_pre_tax:
            return "Pre-Tax"
        elif self.is_taxable:
            return "Taxable"
        elif self.is_hsa:
            return "HSA"
        else:
            return "Post-Tax (Roth)"

    @property
    def effective_employer_match_annual(self):
        """
        Employer match = employer_match_pct % of the employee's annual contribution.
        e.g. employer_match_pct=100 on a $31,000 contribution → $31,000 match (dollar for dollar).
        e.g. employer_match_pct=50 on a $31,000 contribution → $15,500 match.
        Returns 0 if no match configured.
        """
        if not self.employer_match_pct:
            return 0
        return float(self.annual_contribution) * float(self.employer_match_pct) / 100


# ---------------------------------------------------------------------------
# IncomeSource — guaranteed / recurring income streams
# ---------------------------------------------------------------------------

class IncomeSourceType(models.TextChoices):
    SOCIAL_SECURITY = "social_security", "Social Security"
    PENSION         = "pension",         "Pension"
    ANNUITY         = "annuity",         "Annuity"
    IUL             = "iul",             "Indexed Universal Life (IUL)"
    RENTAL          = "rental",          "Rental Property"
    BUSINESS        = "business",        "Business / Royalty"
    PART_TIME       = "part_time",       "Part-Time Work"
    OTHER           = "other",           "Other Income"


class IncomeSource(models.Model):
    """
    A guaranteed or recurring income stream (not a growing investment account).
    Examples: Social Security, pension, IUL distributions, rental income.

    Social Security:  populate ss_monthly_at_67 (FRA benefit from SSA statement); annual_amount left 0.
                      The Scenario supplies claim_age; benefits at other ages are
                      computed via official SSA early-reduction / delayed-credit rules.
    All other types:  populate annual_amount + start_age. SS fields left null.

    IUL note: modeled during distribution phase only (no accumulation/premium logic).
    """
    user_profile  = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="income_sources",
    )
    owner = models.CharField(
        max_length=10,
        choices=[("self", "Primary User"), ("spouse", "Spouse")],
        default="self",
    )
    name        = models.CharField(max_length=200, help_text="e.g. 'Tom's Pension', 'Rental — 123 Main St'")
    source_type = models.CharField(max_length=20, choices=IncomeSourceType.choices)

    # ── Social Security only ──────────────────────────────────────────────────
    ss_monthly_at_67 = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Monthly SS benefit at Full Retirement Age / 67 (from SSA statement)",
    )
    ss_cola_rate = models.DecimalField(
        max_digits=4, decimal_places=2, default=2.5,
        help_text="Annual SS COLA %, default 2.5%",
    )

    # ── All other source types ────────────────────────────────────────────────
    annual_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Annual payout in today's dollars (not used for Social Security)",
    )
    start_age = models.PositiveSmallIntegerField(
        default=65,
        help_text="Age at which this income begins",
    )
    end_age = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Age at which income ends; blank = lifetime / until plan end",
    )

    # ── Growth / inflation ────────────────────────────────────────────────────
    is_inflation_adjusted = models.BooleanField(
        default=False,
        help_text="True = amount grows annually with inflation",
    )
    inflation_rate_override = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True,
        help_text="Override inflation %; blank = use scenario inflation rate",
    )

    # ── Tax treatment ─────────────────────────────────────────────────────────
    is_taxable = models.BooleanField(
        default=True,
        help_text="False = tax-free (e.g. Roth, IUL distributions, HSA medical)",
    )
    tax_rate_override = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Override tax rate %; blank = use scenario retirement tax rate",
    )

    # ── Pension / survivor ────────────────────────────────────────────────────
    survivor_benefit_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Pension survivor benefit % paid to spouse after owner dies (pension only)",
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["source_type", "name"]
        verbose_name = "Income Source"

    def __str__(self):
        return f"{self.name} ({self.get_source_type_display()}) — {self.owner}"

    @property
    def is_social_security(self):
        return self.source_type == IncomeSourceType.SOCIAL_SECURITY

    def monthly_ss_at_claim_age(self, claim_age: int) -> float:
        """
        Compute SS monthly benefit at the given claim age using official SSA rules,
        derived solely from the at-62 benefit on the SSA statement.

        Assumes Full Retirement Age (FRA) = 67 (born 1960 or later).

        Early claiming (62–66):
          First 36 months before FRA: benefit reduced 5/9 of 1% per month.
          Beyond 36 months before FRA: reduced 5/12 of 1% per month.
          → At 62 (60 months early): 36×(5/9%) + 24×(5/12%) = 30% reduction = 70% of FRA.

        Delayed credits (68–70): +8% per year after FRA, up to age 70.
        """
        fra_benefit = float(self.ss_monthly_at_67 or 0)
        if fra_benefit == 0:
            return 0.0

        fra_age = 67
        claim_age = max(62, min(70, claim_age))

        if claim_age == fra_age:
            return fra_benefit
        elif claim_age < fra_age:
            months_before_fra = (fra_age - claim_age) * 12
            if months_before_fra <= 36:
                reduction_pct = months_before_fra * (5 / 9) / 100
            else:
                reduction_pct = (36 * (5 / 9) + (months_before_fra - 36) * (5 / 12)) / 100
            return fra_benefit * (1 - reduction_pct)
        else:
            years_after_fra = claim_age - fra_age
            return fra_benefit * (1 + 0.08 * years_after_fra)
