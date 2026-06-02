import dataclasses
import json
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
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


# ---------------------------------------------------------------------------
# PDF Export
# ---------------------------------------------------------------------------

def _build_svg_chart(years, width=640, height=260):
    """Generate a standalone SVG line chart from year-by-year engine output."""
    if not years:
        return ""

    pad_l, pad_r, pad_t, pad_b = 72, 20, 24, 36

    ages      = [y["age"] for y in years]
    portfolio = [max(0.0, y["total_portfolio"]) for y in years]
    spending  = [y["annual_spending"] for y in years]

    min_age  = ages[0]
    max_age  = ages[-1]
    age_span = max(max_age - min_age, 1)
    max_val  = max(portfolio) * 1.08 if any(v > 0 for v in portfolio) else 1_000_000
    chart_w  = width - pad_l - pad_r
    chart_h  = height - pad_t - pad_b
    bottom   = pad_t + chart_h

    def cx(age):
        return pad_l + (age - min_age) / age_span * chart_w

    def cy(val):
        return pad_t + (1 - min(val, max_val) / max_val) * chart_h

    def fmt_money(v):
        if v >= 1_000_000:
            return f"${v/1_000_000:.1f}M"
        if v >= 1_000:
            return f"${v/1_000:.0f}K"
        return f"${v:.0f}"

    # Grid lines + Y labels
    grid_lines, y_labels = [], []
    y_ticks = 5
    for i in range(y_ticks + 1):
        val = max_val * i / y_ticks
        yp  = cy(val)
        grid_lines.append(
            f'<line x1="{pad_l}" y1="{yp:.1f}" x2="{width-pad_r}" y2="{yp:.1f}" '
            f'stroke="#e5e7eb" stroke-width="0.5"/>'
        )
        y_labels.append(
            f'<text x="{pad_l-6}" y="{yp+3.5:.1f}" text-anchor="end" '
            f'font-size="9" fill="#6b7280">{fmt_money(val)}</text>'
        )

    # X labels every 5 years
    x_labels = []
    for age in range(min_age, max_age + 1, 5):
        xp = cx(age)
        x_labels.append(
            f'<text x="{xp:.1f}" y="{bottom+14}" text-anchor="middle" '
            f'font-size="9" fill="#6b7280">{age}</text>'
        )

    # Portfolio filled area path
    pts = [(cx(a), cy(p)) for a, p in zip(ages, portfolio)]
    area_d = (f"M {pts[0][0]:.1f},{pts[0][1]:.1f} "
              + " ".join(f"L {px:.1f},{py:.1f}" for px, py in pts[1:])
              + f" L {pts[-1][0]:.1f},{bottom} L {pts[0][0]:.1f},{bottom} Z")

    line_d = (f"M {pts[0][0]:.1f},{pts[0][1]:.1f} "
              + " ".join(f"L {px:.1f},{py:.1f}" for px, py in pts[1:]))

    # Spending dashed line
    sp_pts   = " ".join(f"{cx(a):.1f},{cy(s):.1f}" for a, s in zip(ages, spending) if s > 0)
    sp_first = next(((cx(a), cy(s)) for a, s in zip(ages, spending) if s > 0), None)
    sp_path  = ""
    if sp_first:
        sp_data = [(cx(a), cy(s)) for a, s in zip(ages, spending) if s > 0]
        sp_path = (f'<path d="M {sp_data[0][0]:.1f},{sp_data[0][1]:.1f} '
                   + " ".join(f"L {px:.1f},{py:.1f}" for px, py in sp_data[1:])
                   + '" fill="none" stroke="#ef4444" stroke-width="1.2" stroke-dasharray="4,3"/>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
  {"".join(grid_lines)}
  <path d="{area_d}" fill="rgba(79,70,229,0.08)"/>
  <path d="{line_d}" fill="none" stroke="#4f46e5" stroke-width="1.8"/>
  {sp_path}
  <line x1="{pad_l}" y1="{bottom}" x2="{width-pad_r}" y2="{bottom}" stroke="#9ca3af" stroke-width="1"/>
  <line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{bottom}" stroke="#9ca3af" stroke-width="1"/>
  {"".join(y_labels)}
  {"".join(x_labels)}
  <text x="{pad_l + chart_w//2}" y="{height}" text-anchor="middle" font-size="9" fill="#6b7280">Age</text>
  <!-- Legend -->
  <rect x="{pad_l}" y="4" width="12" height="6" fill="#4f46e5" opacity="0.5"/>
  <text x="{pad_l+16}" y="11" font-size="9" fill="#374151">Portfolio Balance</text>
  <line x1="{pad_l+110}" y1="7" x2="{pad_l+122}" y2="7" stroke="#ef4444" stroke-width="1.2" stroke-dasharray="4,3"/>
  <text x="{pad_l+126}" y="11" font-size="9" fill="#374151">Annual Spending</text>
</svg>'''


@login_required
def result_pdf(request, pk):
    """Render the simulation result as a downloadable PDF."""
    from weasyprint import HTML as WeasyprintHTML

    profile  = get_object_or_404(UserProfile, user=request.user)
    result   = get_object_or_404(SimulationResult, pk=pk, scenario__user_profile=profile)
    scenario = result.scenario

    years   = result.result_data.get("years", [])   if result.result_data else []
    summary = result.result_data.get("summary", {}) if result.result_data else {}

    svg_chart = _build_svg_chart(years)

    html_str = render_to_string("simulations/result_pdf.html", {
        "result":       result,
        "scenario":     scenario,
        "profile":      profile,
        "years":        years,
        "summary":      summary,
        "svg_chart":    svg_chart,
        "generated_at": timezone.localtime(timezone.now()),
    }, request=request)

    pdf_bytes = WeasyprintHTML(string=html_str, base_url=request.build_absolute_uri("/")).write_pdf()

    filename = (f"RetireSim-{scenario.name}-"
                f"{timezone.localtime(timezone.now()).strftime('%Y%m%d')}.pdf"
                .replace(" ", "_"))

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
