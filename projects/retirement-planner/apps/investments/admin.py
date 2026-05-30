from django.contrib import admin
from .models import InvestmentAccount


@admin.register(InvestmentAccount)
class InvestmentAccountAdmin(admin.ModelAdmin):
    list_display = ["name", "account_type", "owner", "current_balance", "annual_contribution", "tax_label", "is_active"]
    list_filter = ["account_type", "owner", "is_active"]
    search_fields = ["name", "user_profile__user__email"]
