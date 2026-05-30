"""
Monte Carlo Simulation Engine
------------------------------
Runs N iterations of the deterministic simulation with randomized annual returns.
Returns percentile curves and a success probability.

This is CPU-intensive and MUST be run as a Celery task, not in a web request.

Output schema (result_data):
{
  "schema_version": 1,
  "simulation_type": "monte_carlo",
  "iterations": 1000,
  "success_probability": 87.3,
  "confidence_level": 85,
  "percentiles": {
    "ages": [45, 46, ..., 90],
    "p10": [450000, 480000, ...],
    "p25": [500000, 540000, ...],
    "p50": [600000, 660000, ...],
    "p75": [720000, 800000, ...],
    "p90": [850000, 950000, ...],
  },
  "histogram": {
    "bins": [0, 500000, 1000000, ...],
    "counts": [12, 45, 200, ...]
  },
  "summary": {
    "retirement_age_user": 65,
    "retirement_age_spouse": 63,
    "median_balance_at_retirement": 1100000.0,
    "median_final_balance": 750000.0,
    "success_probability": 87.3,
    "black_swan_avg_events_per_run": 1.2,
  }
}
"""
import random
import copy
import numpy as np
from typing import List, Optional

from .deterministic import SimulationInput, AccountState, run_deterministic
from .black_swan import BlackSwanConfig


def run_monte_carlo(
    inputs: SimulationInput,
    iterations: int = 1000,
    std_dev_stocks_pct: float = 15.0,
    std_dev_bonds_pct: float = 5.0,
    confidence_level: int = 85,
    progress_callback=None,
) -> dict:
    """
    Run Monte Carlo simulation. Returns result_data dict.

    For each iteration:
    - A new random return sequence is generated (normally distributed around the mean)
    - The deterministic engine runs with those returns
    - Results are collected across all iterations

    progress_callback(pct: int) is called periodically if provided (for Celery task updates).
    """
    rng = random.Random()
    results_by_age = {}   # age → list of portfolio values across all runs
    final_balances = []
    balances_at_retirement = []
    success_count = 0
    total_bs_events = 0

    for i in range(iterations):
        # Generate randomized annual returns for this iteration
        # We override the scenario's fixed rates with sampled rates
        iteration_inputs = _randomize_inputs(inputs, std_dev_stocks_pct, std_dev_bonds_pct, rng)

        result = run_deterministic(iteration_inputs, rng=rng)

        # Track success (portfolio never exhausted)
        if not result["summary"]["portfolio_exhausted"]:
            success_count += 1

        # Collect per-age balances
        for year_row in result["years"]:
            age = year_row["age"]
            bal = year_row["total_portfolio"]
            if age not in results_by_age:
                results_by_age[age] = []
            results_by_age[age].append(bal)

        final_balances.append(result["summary"]["final_balance"])
        balances_at_retirement.append(result["summary"]["balance_at_user_retirement"] or 0)
        total_bs_events += len(result["summary"]["black_swan_events"])

        # Progress reporting every 10%
        if progress_callback and (i + 1) % max(1, iterations // 10) == 0:
            pct = int((i + 1) / iterations * 100)
            progress_callback(pct)

    success_probability = (success_count / iterations) * 100

    # Build percentile curves
    ages_sorted = sorted(results_by_age.keys())
    percentile_curves = {
        "ages": ages_sorted,
        "p10": [],
        "p25": [],
        "p50": [],
        "p75": [],
        "p90": [],
    }
    for age in ages_sorted:
        balances = results_by_age[age]
        percentile_curves["p10"].append(round(float(np.percentile(balances, 10)), 2))
        percentile_curves["p25"].append(round(float(np.percentile(balances, 25)), 2))
        percentile_curves["p50"].append(round(float(np.percentile(balances, 50)), 2))
        percentile_curves["p75"].append(round(float(np.percentile(balances, 75)), 2))
        percentile_curves["p90"].append(round(float(np.percentile(balances, 90)), 2))

    # Build final balance histogram
    hist_counts, hist_bins = np.histogram(final_balances, bins=20)
    histogram = {
        "bins": [round(float(b), 2) for b in hist_bins],
        "counts": [int(c) for c in hist_counts],
    }

    # Retirement balance stats
    median_at_retirement = float(np.percentile(balances_at_retirement, 50))
    median_final = float(np.percentile(final_balances, 50))

    return {
        "schema_version": 1,
        "simulation_type": "monte_carlo",
        "iterations": iterations,
        "success_probability": round(success_probability, 2),
        "confidence_level": confidence_level,
        "percentiles": percentile_curves,
        "histogram": histogram,
        "summary": {
            "retirement_age_user": inputs.target_retirement_age,
            "retirement_age_spouse": inputs.spouse_retirement_age,
            "median_balance_at_retirement": round(median_at_retirement, 2),
            "median_final_balance": round(median_final, 2),
            "success_probability": round(success_probability, 2),
            "black_swan_avg_events_per_run": round(total_bs_events / iterations, 2),
        },
    }


def _randomize_inputs(
    base_inputs: SimulationInput,
    std_dev_stocks: float,
    std_dev_bonds: float,
    rng: random.Random,
) -> SimulationInput:
    """
    Create a copy of SimulationInput with accounts that use randomized returns.
    We store the randomized rates as fields for the deterministic engine to use,
    by replacing the scenario-level return rates with sampled values.

    In a full implementation, each YEAR's return is sampled inside the engine.
    Here, we create a modified SimulationInput that the engine interprets to
    sample returns annually via a seeded RNG.

    Approach: We pass the std_dev information through modified inputs.
    The actual per-year sampling happens by setting return_stocks_pct and
    return_bonds_pct per-iteration using the sampled mean (this is a simplified MC;
    a production version would sample per-year returns inside the loop).
    """
    new_inputs = copy.deepcopy(base_inputs)

    # Sample a mean return for this iteration from the distribution
    # (simplified: one return sequence per iteration, same rate each year)
    # For a more realistic MC, the deterministic engine would sample per-year.
    sampled_stocks = rng.gauss(base_inputs.return_stocks_pct, std_dev_stocks)
    sampled_bonds = rng.gauss(base_inputs.return_bonds_pct, std_dev_bonds)

    # Floor at -50% to avoid absurd values
    new_inputs.return_stocks_pct = max(-50.0, sampled_stocks)
    new_inputs.return_bonds_pct = max(-30.0, sampled_bonds)

    return new_inputs
