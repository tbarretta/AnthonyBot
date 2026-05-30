from rest_framework import serializers
from apps.profiles.models import UserProfile, SpouseProfile
from apps.investments.models import InvestmentAccount, IncomeSource
from apps.simulations.models import Scenario, SimulationResult


class SpouseProfileSerializer(serializers.ModelSerializer):
    current_age = serializers.ReadOnlyField()

    class Meta:
        model = SpouseProfile
        exclude = ["user_profile"]


class IncomeSourceSerializer(serializers.ModelSerializer):
    source_type_display = serializers.ReadOnlyField(source="get_source_type_display")
    is_social_security = serializers.ReadOnlyField()

    class Meta:
        model = IncomeSource
        exclude = ["user_profile"]
        read_only_fields = ["created_at", "updated_at"]


class UserProfileSerializer(serializers.ModelSerializer):
    current_age = serializers.ReadOnlyField()
    years_to_retirement = serializers.ReadOnlyField()
    has_spouse = serializers.ReadOnlyField()
    spouse = SpouseProfileSerializer(read_only=True)
    income_sources = IncomeSourceSerializer(many=True, read_only=True)

    class Meta:
        model = UserProfile
        exclude = ["user"]


class InvestmentAccountSerializer(serializers.ModelSerializer):
    tax_label = serializers.ReadOnlyField()
    effective_employer_match_annual = serializers.ReadOnlyField()

    class Meta:
        model = InvestmentAccount
        exclude = ["user_profile"]


class ScenarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scenario
        exclude = ["user_profile"]
        read_only_fields = ["created_at", "updated_at"]


class SimulationResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = SimulationResult
        fields = "__all__"
        read_only_fields = ["result_data", "started_at", "completed_at"]


class SimulationResultStatusSerializer(serializers.ModelSerializer):
    """Lightweight status-only serializer for polling."""
    class Meta:
        model = SimulationResult
        fields = [
            "id", "status", "success_probability",
            "median_balance_at_retirement", "median_balance_at_end",
            "deterministic_final_balance", "portfolio_exhaustion_age",
            "started_at", "completed_at", "error_message",
        ]
