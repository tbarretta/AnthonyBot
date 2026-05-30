from django.contrib import admin
from .models import InvestmentAccount, IncomeSource


@admin.register(InvestmentAccount)
class InvestmentAccountAdmin(admin.ModelAdmin):
    list_display = ["name", "account_type", "owner", "current_balance", "annual_contribution", "tax_label", "is_active"]
    list_filter = ["account_type", "owner", "is_active"]
    search_fields = ["name", "user_profile__user__email"]


@admin.register(IncomeSource)
class IncomeSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "source_type", "owner", "annual_amount", "start_age", "end_age", "is_taxable"]
    list_filter = ["source_type", "owner", "is_taxable", "is_inflation_adjusted"]
    search_fields = ["name", "user_profile__user__email"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = [
        ("Identity", {"fields": ["user_profile", "name", "source_type", "owner"]}),
        ("Social Security", {
            "fields": ["ss_monthly_at_62", "ss_monthly_at_67", "ss_monthly_at_70", "ss_cola_rate"],
            "classes": ["collapse"],
            "description": "Leave blank for non-SS income sources.",
        }),
        ("Amount & Schedule", {
            "fields": ["annual_amount", "start_age", "end_age"],
        }),
        ("Inflation", {
            "fields": ["is_inflation_adjusted", "inflation_rate_override"],
        }),
        ("Tax Treatment", {
            "fields": ["is_taxable", "tax_rate_override"],
        }),
        ("Pension", {
            "fields": ["survivor_benefit_pct"],
            "classes": ["collapse"],
        }),
        ("Notes & Timestamps", {
            "fields": ["notes", "created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]
