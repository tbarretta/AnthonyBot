from django.db import models
from apps.profiles.models import UserProfile


class AccountType(models.TextChoices):
    K401 = "401k", "401(k) — Pre-Tax"
    ROTH_401K = "roth_401k", "Roth 401(k) — Post-Tax"
    TRADITIONAL_IRA = "traditional_ira", "Traditional IRA — Pre-Tax"
    ROTH_IRA = "roth_ira", "Roth IRA — Post-Tax"
    K403B = "403b", "403(b) — Pre-Tax"
    K457 = "457", "457(b) — Pre-Tax"
    PENSION = "pension", "Pension"
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

PENSION_TYPES = {
    AccountType.PENSION,
}


class AccountOwner(models.TextChoices):
    SELF = "self", "Primary User"
    SPOUSE = "spouse", "Spouse"


class InvestmentAccount(models.Model):
    """
    A single investment account (401k, Roth IRA, taxable, etc.).
    Pre-tax vs post-tax drives tax treatment in the simulation engine.
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
    is_pension = models.BooleanField(default=False)

    # Balances & Contributions
    current_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    annual_contribution = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Your annual contribution (pre-tax dollar amount)"
    )

    # Employer Match (applies to 401k-type accounts)
    employer_match_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Employer match rate %, e.g. 50 means 50 cents per dollar contributed"
    )
    employer_match_limit_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Max % of salary employer will match, e.g. 6 means match up to 6% of salary"
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

    # Pension-specific fields
    expected_pension_annual = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Expected annual pension payment (pension accounts only)"
    )
    pension_start_age = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Age at which pension payments begin"
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
        self.is_pension = self.account_type in PENSION_TYPES
        # Post-tax (Roth): not pre-tax, not taxable, not hsa, not pension
        super().save(*args, **kwargs)

    @property
    def tax_label(self):
        if self.is_pre_tax:
            return "Pre-Tax"
        elif self.is_taxable:
            return "Taxable"
        elif self.is_hsa:
            return "HSA"
        elif self.is_pension:
            return "Pension"
        else:
            return "Post-Tax (Roth)"

    @property
    def effective_employer_match_annual(self):
        """
        Compute employer match based on owner's income.
        Returns 0 if no profile income available.
        """
        if not self.employer_match_pct or not self.employer_match_limit_pct:
            return 0
        profile = self.user_profile
        income = float(profile.annual_income if self.owner == "self" else
                       profile.spouse.annual_income if profile.has_spouse else 0)
        max_matchable = income * float(self.employer_match_limit_pct) / 100
        actual_contribution = float(self.annual_contribution)
        matched_contribution = min(actual_contribution, max_matchable)
        return matched_contribution * float(self.employer_match_pct) / 100
