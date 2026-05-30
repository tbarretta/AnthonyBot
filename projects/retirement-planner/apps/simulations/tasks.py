"""
Celery Tasks for Simulations
-----------------------------
Monte Carlo runs here — too slow for a synchronous web request.
"""
from celery import shared_task
from django.utils import timezone

from .models import Scenario, SimulationResult, SimulationStatus
from .services import build_simulation_input
from .engine.monte_carlo import run_monte_carlo


@shared_task(bind=True, name="simulations.run_monte_carlo")
def run_monte_carlo_task(self, scenario_id: int, result_id: int):
    """
    Celery task: run Monte Carlo simulation and store results.
    Called by the view after creating a pending SimulationResult.
    """
    try:
        scenario = Scenario.objects.select_related("user_profile__user").get(pk=scenario_id)
        result = SimulationResult.objects.get(pk=result_id)

        result.status = SimulationStatus.RUNNING
        result.started_at = timezone.now()
        result.save(update_fields=["status", "started_at"])

        inputs = build_simulation_input(scenario)

        def progress_cb(pct: int):
            self.update_state(state="PROGRESS", meta={"percent": pct})

        data = run_monte_carlo(
            inputs=inputs,
            iterations=scenario.mc_iterations,
            std_dev_stocks_pct=float(scenario.mc_return_std_dev_stocks),
            std_dev_bonds_pct=float(scenario.mc_return_std_dev_bonds),
            confidence_level=scenario.mc_confidence_level,
            progress_callback=progress_cb,
        )

        summary = data["summary"]
        result.status = SimulationStatus.COMPLETE
        result.result_data = data
        result.success_probability = summary["success_probability"]
        result.median_balance_at_retirement = summary["median_balance_at_retirement"]
        result.median_balance_at_end = summary["median_final_balance"]
        result.completed_at = timezone.now()
        result.save()

    except Scenario.DoesNotExist:
        pass
    except Exception as exc:
        SimulationResult.objects.filter(pk=result_id).update(
            status=SimulationStatus.FAILED,
            error_message=str(exc),
            completed_at=timezone.now(),
        )
        raise
