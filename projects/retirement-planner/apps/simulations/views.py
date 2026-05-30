import json
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from apps.profiles.models import UserProfile
from .forms import ScenarioForm
from .models import Scenario, SimulationResult, SimulationStatus
from .services import run_deterministic_sync
from .tasks import run_monte_carlo_task


@login_required
def scenario_list(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    scenarios = Scenario.objects.filter(user_profile=profile).prefetch_related("results")
    return render(request, "simulations/scenario_list.html", {
        "scenarios": scenarios,
        "profile": profile,
    })


@login_required
def scenario_create(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if request.method == "POST":
        form = ScenarioForm(request.POST, profile=profile)
        if form.is_valid():
            scenario = form.save(commit=False)
            scenario.user_profile = profile
            scenario.save()
            messages.success(request, f"Scenario '{scenario.name}' created.")
            return redirect("simulations:detail", pk=scenario.pk)
    else:
        form = ScenarioForm(profile=profile)
    return render(request, "simulations/scenario_form.html", {"form": form, "profile": profile})


@login_required
def scenario_edit(request, pk):
    profile = get_object_or_404(UserProfile, user=request.user)
    scenario = get_object_or_404(Scenario, pk=pk, user_profile=profile)
    if request.method == "POST":
        form = ScenarioForm(request.POST, instance=scenario, profile=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Scenario updated.")
            return redirect("simulations:detail", pk=scenario.pk)
    else:
        form = ScenarioForm(instance=scenario, profile=profile)
    return render(request, "simulations/scenario_form.html", {
        "form": form, "scenario": scenario, "profile": profile
    })


@login_required
def scenario_detail(request, pk):
    profile = get_object_or_404(UserProfile, user=request.user)
    scenario = get_object_or_404(Scenario, pk=pk, user_profile=profile)
    latest_result = scenario.latest_result
    return render(request, "simulations/scenario_detail.html", {
        "scenario": scenario,
        "latest_result": latest_result,
        "profile": profile,
    })


@login_required
def scenario_delete(request, pk):
    profile = get_object_or_404(UserProfile, user=request.user)
    scenario = get_object_or_404(Scenario, pk=pk, user_profile=profile)
    if request.method == "POST":
        name = scenario.name
        scenario.delete()
        messages.success(request, f"Scenario '{name}' deleted.")
        return redirect("simulations:list")
    return render(request, "simulations/scenario_confirm_delete.html", {"scenario": scenario})


@login_required
def run_simulation(request, pk):
    """
    Trigger a simulation run for a scenario.
    - Deterministic: runs synchronously, redirects to results
    - Monte Carlo: dispatches Celery task, returns task ID for polling
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    scenario = get_object_or_404(Scenario, pk=pk, user_profile=profile)

    if scenario.simulation_type == "deterministic":
        result = run_deterministic_sync(scenario)
        if request.headers.get("HX-Request"):
            return render(request, "simulations/partials/result_summary.html", {
                "result": result, "scenario": scenario
            })
        return redirect("simulations:result_detail", pk=result.pk)

    else:  # monte_carlo
        result = SimulationResult.objects.create(
            scenario=scenario,
            status=SimulationStatus.PENDING,
        )
        run_monte_carlo_task.delay(scenario.pk, result.pk)
        if request.headers.get("HX-Request"):
            return render(request, "simulations/partials/mc_polling.html", {
                "result": result, "scenario": scenario
            })
        return redirect("simulations:result_detail", pk=result.pk)


@login_required
def result_status(request, pk):
    """HTMX polling endpoint — returns current status of a simulation result."""
    profile = get_object_or_404(UserProfile, user=request.user)
    result = get_object_or_404(SimulationResult, pk=pk, scenario__user_profile=profile)

    if request.headers.get("HX-Request"):
        if result.status == SimulationStatus.COMPLETE:
            return render(request, "simulations/partials/result_summary.html", {
                "result": result, "scenario": result.scenario
            })
        elif result.status == SimulationStatus.FAILED:
            return render(request, "simulations/partials/result_error.html", {"result": result})
        else:
            return render(request, "simulations/partials/mc_polling.html", {
                "result": result, "scenario": result.scenario
            })

    return JsonResponse({
        "status": result.status,
        "success_probability": str(result.success_probability) if result.success_probability else None,
        "median_balance_at_retirement": str(result.median_balance_at_retirement) if result.median_balance_at_retirement else None,
    })


@login_required
def result_detail(request, pk):
    profile = get_object_or_404(UserProfile, user=request.user)
    result = get_object_or_404(SimulationResult, pk=pk, scenario__user_profile=profile)
    scenario = result.scenario

    # Prepare chart data
    chart_data = _build_chart_data(result)

    return render(request, "simulations/result_detail.html", {
        "result": result,
        "scenario": scenario,
        "profile": profile,
        "chart_data_json": json.dumps(chart_data),
    })


def _build_chart_data(result: SimulationResult) -> dict:
    """Extract chart-ready data from result_data JSON."""
    data = result.result_data
    if not data:
        return {}

    if data.get("simulation_type") == "deterministic":
        years = data.get("years", [])
        return {
            "type": "deterministic",
            "labels": [str(y["year"]) for y in years],
            "ages": [y["age"] for y in years],
            "total_portfolio": [y["total_portfolio"] for y in years],
            "ss_income": [y["ss_income"] for y in years],
            "pension_income": [y["pension_income"] for y in years],
            "annual_spending": [y["annual_spending"] for y in years],
            "total_contributions": [y["total_contributions"] for y in years],
            "black_swan_events": [
                {"age": y["age"], "event": y["black_swan_event"]}
                for y in years if y.get("black_swan_event")
            ],
        }
    else:  # monte_carlo
        pcts = data.get("percentiles", {})
        return {
            "type": "monte_carlo",
            "ages": pcts.get("ages", []),
            "p10": pcts.get("p10", []),
            "p25": pcts.get("p25", []),
            "p50": pcts.get("p50", []),
            "p75": pcts.get("p75", []),
            "p90": pcts.get("p90", []),
            "histogram": data.get("histogram", {}),
            "success_probability": data.get("success_probability"),
        }
