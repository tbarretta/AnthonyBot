import dataclasses
import json
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from apps.profiles.models import UserProfile
from .forms import ScenarioForm
from .models import Scenario, SimulationResult, SimulationStatus
from .services import run_deterministic_sync, build_simulation_input
from .engine.deterministic import run_deterministic
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
            return redirect("simulations:run", pk=scenario.pk)
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
            return redirect("simulations:run", pk=scenario.pk)
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
def scenario_copy(request, pk):
    profile = get_object_or_404(UserProfile, user=request.user)
    original = get_object_or_404(Scenario, pk=pk, user_profile=profile)

    # Duplicate: clear pk so Django inserts a new row
    original.pk = None
    original.name = f"{original.name}-copy"
    original.save()

    messages.success(request, f"Scenario copied as '{original.name}'. Make your adjustments and save.")
    return redirect("simulations:edit", pk=original.pk)


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

    # Monte Carlo is implemented but not yet exposed in the UI.
    # All scenarios run deterministically for now.
    result = run_deterministic_sync(scenario)
    if request.headers.get("HX-Request"):
        return render(request, "simulations/partials/result_summary.html", {
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

    years = result.result_data.get("years", []) if result.result_data else []

    base_spending = float(scenario.annual_retirement_spending)
    spending_min = max(500, int(base_spending * 0.5 / 500) * 500)
    spending_max = int(base_spending * 1.5 / 500 + 1) * 500

    return render(request, "simulations/result_detail.html", {
        "result": result,
        "scenario": scenario,
        "profile": profile,
        "chart_data_json": json.dumps(chart_data),
        "years": years,
        "base_spending": base_spending,
        "spending_min": spending_min,
        "spending_max": spending_max,
        "base_stocks": float(scenario.expected_annual_return_stocks),
        "base_bonds": float(scenario.expected_annual_return_bonds),
    })


def _build_chart_data_from_raw(data: dict) -> dict:
    """Build chart-ready data dict from raw engine output."""
    if not data:
        return {}
    if data.get("simulation_type") == "deterministic":
        years = data.get("years", [])
        return {
            "type": "deterministic",
            "labels": [str(y["year"]) for y in years],
            "ages": [y["age"] for y in years],
            "total_portfolio": [y["total_portfolio"] for y in years],
            "ss_income": [y.get("ss_income", 0) for y in years],
            "pension_income": [y.get("pension_income", 0) for y in years],
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


def _build_chart_data(result: SimulationResult) -> dict:
    """Extract chart-ready data from a SimulationResult."""
    return _build_chart_data_from_raw(result.result_data)


@login_required
def sensitivity_update(request, pk):
    """
    HTMX endpoint for sensitivity sliders.
    Re-runs deterministic engine with overridden spending / return rates.
    Does NOT save a new SimulationResult — purely ephemeral.
    """
    if not request.headers.get("HX-Request"):
        return redirect("simulations:result_detail", pk=pk)

    profile = get_object_or_404(UserProfile, user=request.user)
    result = get_object_or_404(SimulationResult, pk=pk, scenario__user_profile=profile)
    scenario = result.scenario

    try:
        spending = float(request.GET.get("spending", scenario.annual_retirement_spending))
        stocks   = float(request.GET.get("stocks",   scenario.expected_annual_return_stocks))
        bonds    = float(request.GET.get("bonds",    scenario.expected_annual_return_bonds))
    except (TypeError, ValueError):
        spending = float(scenario.annual_retirement_spending)
        stocks   = float(scenario.expected_annual_return_stocks)
        bonds    = float(scenario.expected_annual_return_bonds)

    sim_input = build_simulation_input(scenario)
    sim_input = dataclasses.replace(
        sim_input,
        annual_retirement_spending=spending,
        return_stocks_pct=stocks,
        return_bonds_pct=bonds,
    )

    data    = run_deterministic(sim_input)
    summary = data["summary"]

    life_expectancy = scenario.user_life_expectancy_age or profile.life_expectancy_age

    return render(request, "simulations/partials/sensitivity_result.html", {
        "summary":            summary,
        "scenario":           scenario,
        "profile":            profile,
        "chart_data_json":    json.dumps(_build_chart_data_from_raw(data)),
        "final_balance":      summary["final_balance"],
        "balance_at_retirement": summary["balance_at_user_retirement"],
        "exhaustion_age":     summary.get("exhaustion_age"),
        "life_expectancy":    life_expectancy,
        "spending_override":  spending,
        "stocks_override":    stocks,
        "bonds_override":     bonds,
        "years":              data.get("years", []),
        "black_swan_events":  summary.get("black_swan_events", []),
    })


# Colours assigned to each scenario slot (indigo / emerald / amber)
_COMPARE_COLORS = [
    {"border": "#4f46e5", "bg": "rgba(79,70,229,0.08)",  "tailwind": "indigo"},
    {"border": "#10b981", "bg": "rgba(16,185,129,0.08)", "tailwind": "emerald"},
    {"border": "#f59e0b", "bg": "rgba(245,158,11,0.08)", "tailwind": "amber"},
]

_COMPARE_ASSUMPTIONS = [
    ("Retirement Age",       lambda s: s.retirement_age_self,               None),
    ("SS Claim Age",         lambda s: s.ss_claim_age_self,                  None),
    ("Annual Spending",      lambda s: float(s.annual_retirement_spending),  "currency"),
    ("Spending Strategy",    lambda s: s.get_spending_strategy_display(),    None),
    ("Stock Return",         lambda s: float(s.expected_annual_return_stocks), "pct"),
    ("Bond Return",          lambda s: float(s.expected_annual_return_bonds),  "pct"),
    ("Inflation Rate",       lambda s: float(s.inflation_rate),              "pct"),
    ("Tax Rate (Working)",   lambda s: float(s.effective_tax_rate_working),  "pct"),
    ("Tax Rate (Retirement)",lambda s: float(s.effective_tax_rate_retirement),"pct"),
    ("Black Swan",           lambda s: "Yes" if s.black_swan_enabled else "No", None),
    ("Guardrails",           lambda s: "Yes" if s.guardrails_enabled else "No", None),
]


@login_required
def scenario_compare(request):
    profile = get_object_or_404(UserProfile, user=request.user)

    raw_ids = request.GET.getlist("s")
    if len(raw_ids) < 2 or len(raw_ids) > 3:
        messages.error(request, "Select 2 or 3 scenarios to compare.")
        return redirect("simulations:list")

    scenarios = []
    for sid in raw_ids:
        try:
            scenarios.append(
                Scenario.objects.get(pk=int(sid), user_profile=profile)
            )
        except (Scenario.DoesNotExist, ValueError):
            messages.error(request, "One or more selected scenarios were not found.")
            return redirect("simulations:list")

    # Run each scenario fresh
    run_results = []
    for scenario in scenarios:
        sim_input = build_simulation_input(scenario)
        data = run_deterministic(sim_input)
        run_results.append(data)

    # Build chart datasets (one line per scenario)
    chart_datasets = []
    for i, (scenario, data) in enumerate(zip(scenarios, run_results)):
        color = _COMPARE_COLORS[i]
        years = data.get("years", [])
        chart_datasets.append({
            "label":           scenario.name,
            "ages":            [y["age"] for y in years],
            "total_portfolio": [y["total_portfolio"] for y in years],
            "annual_spending": [y["annual_spending"] for y in years],
            "borderColor":     color["border"],
            "backgroundColor": color["bg"],
        })

    # Build assumptions comparison rows
    assumption_rows = []
    for label, getter, fmt in _COMPARE_ASSUMPTIONS:
        values = [getter(s) for s in scenarios]
        assumption_rows.append({
            "label":  label,
            "values": values,
            "format": fmt,
            "differs": len(set(str(v) for v in values)) > 1,
        })

    # Summary rows
    summaries = [r["summary"] for r in run_results]

    # Zip scenarios + summaries + colors for easy template iteration
    scenario_results = [
        {
            "scenario": scenario,
            "summary":  run_results[i]["summary"],
            "color":    _COMPARE_COLORS[i],
            "slot":     i + 1,   # 1-indexed for CSS class selection
        }
        for i, scenario in enumerate(scenarios)
    ]

    return render(request, "simulations/compare.html", {
        "scenario_results": scenario_results,
        "assumption_rows":  assumption_rows,
        "chart_data_json":  json.dumps({"datasets": chart_datasets}),
        "profile":          profile,
        "query_string":     request.GET.urlencode(),
    })
