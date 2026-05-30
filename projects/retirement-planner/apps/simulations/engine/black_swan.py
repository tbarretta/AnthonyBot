"""
Black Swan Event Engine
-----------------------
Models rare, severe market disruptions (crashes, crises).
Each year independently draws whether a black swan strikes.
Recovery is modeled as suppressed returns over N years post-event.
"""
import random
from dataclasses import dataclass, field
from typing import List


@dataclass
class BlackSwanConfig:
    enabled: bool = False
    annual_probability_pct: float = 3.0      # e.g. 3.0 = 3% per year
    min_loss_pct: float = 20.0               # minimum portfolio loss %
    max_loss_pct: float = 50.0              # maximum portfolio loss %
    recovery_years: int = 3                  # avg years for suppressed returns post-event


@dataclass
class BlackSwanState:
    """Tracks active black swan recovery periods across simulation years."""
    active_recoveries: List[int] = field(default_factory=list)  # years remaining per active event
    events_triggered: List[dict] = field(default_factory=list)  # audit log


def check_and_apply_black_swan(
    year: int,
    age: int,
    portfolio_value: float,
    config: BlackSwanConfig,
    state: BlackSwanState,
    rng: random.Random = None,
) -> tuple[float, BlackSwanState, dict | None]:
    """
    For a given simulation year:
    1. Check if a new black swan event triggers
    2. If yes, apply portfolio loss and start a recovery period
    3. Return (modified_portfolio_value, updated_state, event_info_or_None)
    """
    if not config.enabled or portfolio_value <= 0:
        return portfolio_value, state, None

    rng = rng or random

    event_info = None

    # Check if a new black swan event fires this year
    if rng.random() < (config.annual_probability_pct / 100.0):
        loss_pct = rng.uniform(config.min_loss_pct, config.max_loss_pct)
        loss_amount = portfolio_value * (loss_pct / 100.0)
        portfolio_value = max(0.0, portfolio_value - loss_amount)

        state.active_recoveries.append(config.recovery_years)
        event_info = {
            "year": year,
            "age": age,
            "loss_pct": round(loss_pct, 2),
            "loss_amount": round(loss_amount, 2),
            "portfolio_after": round(portfolio_value, 2),
        }
        state.events_triggered.append(event_info)

    return portfolio_value, state, event_info


def get_return_suppression_factor(state: BlackSwanState) -> float:
    """
    Returns a multiplier to apply to annual returns during recovery.
    Each active recovery suppresses returns by a fraction.
    E.g. 1 active recovery → returns are 60% of normal.
         2 overlapping recoveries → returns are 36% of normal.
    Recoveries decrement by 1 each year.
    """
    if not state.active_recoveries:
        return 1.0

    suppression_per_event = 0.40  # 40% suppression per active recovery
    factor = 1.0
    for _ in state.active_recoveries:
        factor *= (1.0 - suppression_per_event)
    return max(0.1, factor)  # floor at 10% to avoid completely zeroing returns


def advance_recoveries(state: BlackSwanState) -> BlackSwanState:
    """
    Tick down recovery counters at year end. Remove completed recoveries.
    """
    state.active_recoveries = [r - 1 for r in state.active_recoveries if r > 1]
    return state
