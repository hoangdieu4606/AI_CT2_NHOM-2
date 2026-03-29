from __future__ import annotations

from typing import Callable, Dict, List, Optional

from algorithms.cso.cso_solver import solve as solve_cso
from algorithms.ga.ga_solver import solve as solve_ga
from core.models import KnapsackInstance
from experiments.scenarios import get_cso_scenarios, get_ga_scenarios
from experiments.statistics import summarize_numeric


def run_benchmark_in_memory(
    instance: KnapsackInstance,
    scenario_key: str,
    n_runs: int = 3,
    seed_base: int = 123,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Dict:
    """
    Chạy benchmark theo yêu cầu thầy:
    - Chỉ so sánh nội bộ GA với GA, CSO với CSO
    - progress_callback(current, total, case_name) để cập nhật UI
    """
    ga_scenarios = get_ga_scenarios()
    cso_scenarios = get_cso_scenarios()

    if scenario_key in ga_scenarios:
        algorithm = "GA"
        scenario_cases = ga_scenarios[scenario_key]
        solver = solve_ga
    elif scenario_key in cso_scenarios:
        algorithm = "CSO"
        scenario_cases = cso_scenarios[scenario_key]
        solver = solve_cso
    else:
        raise ValueError(f"Unknown scenario: {scenario_key}")

    total_steps = len(scenario_cases) * n_runs
    current_step = 0
    case_summaries: List[Dict] = []

    for case_name, variable_config in scenario_cases:
        results = []
        for run_idx in range(n_runs):
            seed = seed_base + run_idx
            results.append(solver(instance, variable_config, seed=seed))
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, case_name)

        case_summaries.append({
            "case_name": case_name,
            "algorithm": algorithm,
            "config": variable_config,
            "runtime": summarize_numeric([r.runtime_sec for r in results]),
            "value":   summarize_numeric([r.best_value   for r in results]),
        })

    return {
        "algorithm":     algorithm,
        "scenario_key":  scenario_key,
        "instance_name": instance.name,
        "difficulty":    instance.difficulty,
        "items":         len(instance.items),
        "capacity":      instance.capacity,
        "n_runs":        n_runs,
        "cases":         case_summaries,
    }