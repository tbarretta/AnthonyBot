from django.db import models
from django.conf import settings
from django.utils import timezone
import datetime


class FilingStatus(models.TextChoices):
    SINGLE = "single", "Single"
    MARRIED_JOINTLY = "married_jointly", "Married Filing Jointly"
    MARRIED_SEPARATELY = "married_separately", "Married Filing Separately"
    HEAD_OF_HOUSEHOLD = "head_of_household", "Head of Household"


class UserProfile(models.Model):
    """
    Core financial profile for the primary user.
    Demographic and income facts only — retirement age lives on Scenario.
    All monetary values in USD. Percentages stored as decimals (7.5 = 7.5%).
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

    # Employment & Income
    annual_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    income_growth_rate = models.DecimalField(
        max_digits=4, decimal_places=1, default=3.0,
        help_text="Expected annual raise %, e.g. 3.0"
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
        max_digits=4, decimal_places=1, default=3.0,
        help_text="Expected annual raise %, e.g. 3.0"
    )

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


# SocialSecurityEstimate was moved to apps.simulations.models (Scenario).
# SS data is now configured per-scenario, not per-profile.
