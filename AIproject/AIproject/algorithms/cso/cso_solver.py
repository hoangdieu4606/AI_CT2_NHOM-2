from __future__ import annotations

import random
import time
from typing import Dict, List

from algorithms.cso.decoder import evaluate_position
from algorithms.cso.seeking import seeking_step
from algorithms.cso.tracing import tracing_step
from core.models import KnapsackInstance, OptimizationResult


def solve(instance: KnapsackInstance, config: Dict | None = None, seed: int = 42) -> OptimizationResult:
    config = config or {}
    rng = random.Random(seed)

    num_cats = int(config.get("num_cats", 50))
    max_iter = int(config.get("max_iter", 200))
    mr = float(config.get("mr", 0.2))
    pos_min = float(config.get("pos_min", -5.12))
    pos_max = float(config.get("pos_max", 5.12))
    use_delta_stop = bool(config.get("use_delta_stop", False))
    delta_iterations = int(config.get("delta_iterations", 20))
    delta_min_improvement = float(config.get("delta_min_improvement", 1e-6))

    dimension = len(instance.items)
    positions: List[List[float]] = [
        [rng.uniform(pos_min, pos_max) for _ in range(dimension)]
        for _ in range(num_cats)
    ]
    velocities: List[List[float]] = [[0.0] * dimension for _ in range(num_cats)]

    pbest_positions = [pos[:] for pos in positions]
    pbest_bits = []
    pbest_values = []
    pbest_weights = []
    pbest_feasible = []

    for pos in positions:
        bits, value, weight, feasible = evaluate_position(pos, instance)
        pbest_bits.append(bits)
        pbest_values.append(value)
        pbest_weights.append(weight)
        pbest_feasible.append(feasible)

    best_idx = max(range(num_cats), key=lambda i: pbest_values[i])
    gbest_position = pbest_positions[best_idx][:]
    gbest_bits = pbest_bits[best_idx][:]
    gbest_value = pbest_values[best_idx]
    gbest_weight = pbest_weights[best_idx]
    gbest_feasible = pbest_feasible[best_idx]

    history_best = []
    history_avg = []
    start_time = time.perf_counter()

    stagnant_iterations = 0
    last_checkpoint_best = gbest_value

    for iteration in range(max_iter):
        flags = [0 if i < int((1 - mr) * num_cats) else 1 for i in range(num_cats)]
        rng.shuffle(flags)

        current_values = []

        for i in range(num_cats):
            if flags[i] == 0:
                new_pos, bits, value, weight, feasible = seeking_step(positions[i], instance, config, rng)
                positions[i] = new_pos
            else:
                new_pos, new_vel = tracing_step(positions[i], velocities[i], gbest_position, config, rng)
                positions[i] = new_pos
                velocities[i] = new_vel
                bits, value, weight, feasible = evaluate_position(new_pos, instance)

            current_values.append(value)

            if value > pbest_values[i]:
                pbest_positions[i] = positions[i][:]
                pbest_bits[i] = bits[:]
                pbest_values[i] = value
                pbest_weights[i] = weight
                pbest_feasible[i] = feasible

            if value > gbest_value:
                gbest_position = positions[i][:]
                gbest_bits = bits[:]
                gbest_value = value
                gbest_weight = weight
                gbest_feasible = feasible

        history_best.append(gbest_value)
        history_avg.append(sum(current_values) / len(current_values))

        if use_delta_stop:
            if gbest_value - last_checkpoint_best > delta_min_improvement:
                stagnant_iterations = 0
                last_checkpoint_best = gbest_value
            else:
                stagnant_iterations += 1
                if stagnant_iterations >= delta_iterations:
                    break

    runtime = time.perf_counter() - start_time
    return OptimizationResult(
        algorithm="CSO",
        best_solution=gbest_bits,
        best_value=gbest_value,
        best_weight=gbest_weight,
        is_feasible=gbest_feasible,
        runtime_sec=runtime,
        history_best=history_best,
        history_avg=history_avg,
        meta={
            "config": {
                "num_cats": num_cats,
                "max_iter": max_iter,
                "mr": mr,
                "smp": int(config.get("smp", 5)),
                "srd": float(config.get("srd", 0.2)),
                "cdc": int(config.get("cdc", 3)),
                "c1": float(config.get("c1", 0.5)),
                "use_delta_stop": use_delta_stop,
                "delta_iterations": delta_iterations,
                "delta_min_improvement": delta_min_improvement,
                "executed_iterations": len(history_best),
            }
        }
    )
