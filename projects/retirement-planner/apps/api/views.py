from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.profiles.models import UserProfile, SpouseProfile
from apps.investments.models import InvestmentAccount
from apps.simulations.models import Scenario, SimulationResult, SimulationStatus
from apps.simulations.services import run_deterministic_sync
from apps.simulations.tasks import run_monte_carlo_task

from .serializers import (
    UserProfileSerializer, SpouseProfileSerializer,
    InvestmentAccountSerializer, ScenarioSerializer,
    SimulationResultSerializer, SimulationResultStatusSerializer,
)


# ----- Profile -----

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(UserProfile, user=self.request.user)


class SpouseView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SpouseProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        profile = get_object_or_404(UserProfile, user=self.request.user)
        return get_object_or_404(SpouseProfile, user_profile=profile)

    def perform_create(self, serializer):
        profile = get_object_or_404(UserProfile, user=self.request.user)
        serializer.save(user_profile=profile)

    def post(self, request, *args, **kwargs):
        profile = get_object_or_404(UserProfile, user=request.user)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user_profile=profile)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ----- Investments -----

class InvestmentAccountListCreateView(generics.ListCreateAPIView):
    serializer_class = InvestmentAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = get_object_or_404(UserProfile, user=self.request.user)
        return InvestmentAccount.objects.filter(user_profile=profile)

    def perform_create(self, serializer):
        profile = get_object_or_404(UserProfile, user=self.request.user)
        serializer.save(user_profile=profile)


class InvestmentAccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = InvestmentAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = get_object_or_404(UserProfile, user=self.request.user)
        return InvestmentAccount.objects.filter(user_profile=profile)


# ----- Simulations -----

class ScenarioListCreateView(generics.ListCreateAPIView):
    serializer_class = ScenarioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = get_object_or_404(UserProfile, user=self.request.user)
        return Scenario.objects.filter(user_profile=profile)

    def perform_create(self, serializer):
        profile = get_object_or_404(UserProfile, user=self.request.user)
        serializer.save(user_profile=profile)


class ScenarioDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ScenarioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = get_object_or_404(UserProfile, user=self.request.user)
        return Scenario.objects.filter(user_profile=profile)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def run_scenario(request, pk):
    """Trigger a simulation run. Returns result id for polling."""
    profile = get_object_or_404(UserProfile, user=request.user)
    scenario = get_object_or_404(Scenario, pk=pk, user_profile=profile)

    if scenario.simulation_type == "deterministic":
        result = run_deterministic_sync(scenario)
        return Response(SimulationResultSerializer(result).data, status=status.HTTP_201_CREATED)
    else:
        result = SimulationResult.objects.create(
            scenario=scenario,
            status=SimulationStatus.PENDING,
        )
        run_monte_carlo_task.delay(scenario.pk, result.pk)
        return Response(
            {"result_id": result.pk, "status": "pending"},
            status=status.HTTP_202_ACCEPTED,
        )


class SimulationResultDetailView(generics.RetrieveAPIView):
    serializer_class = SimulationResultSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = get_object_or_404(UserProfile, user=self.request.user)
        return SimulationResult.objects.filter(scenario__user_profile=profile)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def result_status(request, pk):
    """Lightweight polling endpoint — returns status + summary stats only."""
    profile = get_object_or_404(UserProfile, user=request.user)
    result = get_object_or_404(SimulationResult, pk=pk, scenario__user_profile=profile)
    serializer = SimulationResultStatusSerializer(result)
    return Response(serializer.data)
