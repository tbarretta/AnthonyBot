from django.db import models
from django.conf import settings
from django.utils import timezone
import datetime


class FilingStatus(models.TextChoices):
    SINGLE = "single", "Single"
    MARRIED_JOINTLY = "married_jointly", "Married Filing Jointly"
    MARRIED_SEPARATELY = "married_separately", "Married Filing Separately"
    HEAD_OF_HOUSEHOLD = "head_of_household", "Head of Household"


class RiskTolerance(models.TextChoices):
    CONSERVATIVE = "conservative", "Conservative"
    MODERATE = "moderate", "Moderate"
    AGGRESSIVE = "aggressive", "Aggressive"


class UserProfile(models.Model):
    """
    Core financial profile for the primary user.
    All monetary values in USD. All percentages stored as decimals (7.5 = 7.5%).
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    # Personal
    birth_date = models.DateField()
    state = models.CharField(max_length=2, help_text="2-letter state code for tax estimates")
    filing_status = models.CharField(max_length=30, choices=FilingStatus.choices, default=FilingStatus.SINGLE)
    risk_tolerance = models.CharField(max_length=20, choices=RiskTolerance.choices, default=RiskTolerance.MODERATE)

    # Employment & Income
    annual_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    income_growth_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=3.0,
        help_text="Expected annual raise %, e.g. 3.0"
    )
    target_retirement_age = models.PositiveSmallIntegerField(default=65)
    income_end_age = models.PositiveSmallIntegerField(
        default=65,
        help_text="Age at which primary income stops (usually = retirement age)"
    )

    # Longevity
    life_expectancy_age = models.PositiveSmallIntegerField(default=90)

    # Profile completeness flag
    is_setup_complete = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"

    def __str__(self):
        return f"Profile — {self.user.email}"

    @property
    def current_age(self):
        today = datetime.date.today()
        born = self.birth_date
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    @property
    def years_to_retirement(self):
        return max(0, self.target_retirement_age - self.current_age)

    @property
    def has_spouse(self):
        return hasattr(self, "spouse")


class SpouseProfile(models.Model):
    """
    Optional spouse/partner data linked to a UserProfile.
    """
    user_profile = models.OneToOneField(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="spouse",
    )

    first_name = models.CharField(max_length=100)
    birth_date = models.DateField()

    # Employment & Income
    annual_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    income_growth_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=3.0,
        help_text="Expected annual raise %, e.g. 3.0"
    )
    target_retirement_age = models.PositiveSmallIntegerField(default=65)
    income_end_age = models.PositiveSmallIntegerField(default=65)

    # Longevity
    life_expectancy_age = models.PositiveSmallIntegerField(default=90)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Spouse Profile"

    def __str__(self):
        return f"Spouse — {self.first_name} ({self.user_profile.user.email})"

    @property
    def current_age(self):
        today = datetime.date.today()
        born = self.birth_date
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


class SSOwner(models.TextChoices):
    SELF = "self", "Primary User"
    SPOUSE = "spouse", "Spouse"


class SocialSecurityEstimate(models.Model):
    """
    Social Security benefit estimate for user and/or spouse.
    Stores benefits at key claiming ages; user selects their intended claim age.
    """
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="ss_estimates",
    )
    owner = models.CharField(max_length=10, choices=SSOwner.choices, default=SSOwner.SELF)

    # Monthly benefit estimates (in today's dollars)
    monthly_benefit_at_62 = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    monthly_benefit_at_67 = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Full Retirement Age (FRA) benefit"
    )
    monthly_benefit_at_70 = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Intended claim age
    claim_age = models.PositiveSmallIntegerField(
        default=67,
        help_text="Age at which this person intends to claim SS benefits"
    )

    # Cost-of-living adjustment
    cola_rate = models.DecimalField(
        max_digits=4, decimal_places=2, default=2.5,
        help_text="Annual COLA rate %, default 2.5%"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["user_profile", "owner"]]
        verbose_name = "Social Security Estimate"

    def __str__(self):
        return f"SS Estimate — {self.get_owner_display()} ({self.user_profile.user.email})"

    def monthly_benefit_at_claim_age(self):
        """Interpolate/select benefit based on claim_age."""
        if self.claim_age <= 62:
            return self.monthly_benefit_at_62
        elif self.claim_age >= 70:
            return self.monthly_benefit_at_70
        elif self.claim_age < 67:
            # Linear interpolation between 62 and 67
            fraction = (self.claim_age - 62) / (67 - 62)
            return self.monthly_benefit_at_62 + fraction * (self.monthly_benefit_at_67 - self.monthly_benefit_at_62)
        else:
            # Linear interpolation between 67 and 70
            fraction = (self.claim_age - 67) / (70 - 67)
            return self.monthly_benefit_at_67 + fraction * (self.monthly_benefit_at_70 - self.monthly_benefit_at_67)
