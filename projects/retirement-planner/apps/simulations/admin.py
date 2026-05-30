from django.contrib import admin
from .models import Scenario, SimulationResult


class ResultInline(admin.TabularInline):
    model = SimulationResult
    extra = 0
    readonly_fields = ["status", "success_probability", "median_balance_at_retirement", "completed_at"]
    can_delete = False


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ["name", "user_profile", "simulation_type", "black_swan_enabled", "updated_at"]
    list_filter = ["simulation_type", "black_swan_enabled"]
    search_fields = ["name", "user_profile__user__email"]
    inlines = [ResultInline]


@admin.register(SimulationResult)
class SimulationResultAdmin(admin.ModelAdmin):
    list_display = ["scenario", "status", "success_probability", "median_balance_at_retirement", "completed_at"]
    list_filter = ["status"]
    readonly_fields = ["result_data", "started_at", "completed_at"]
