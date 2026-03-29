from __future__ import annotations

import random
from typing import Dict, List, Sequence, Tuple

from algorithms.cso.decoder import evaluate_position
from core.models import KnapsackInstance


def generate_candidate(position: Sequence[float], cdc: int, srd: float, rng: random.Random, pos_min: float, pos_max: float) -> List[float]:
    candidate = list(position)
    dim_count = len(candidate)
    cdc = max(1, min(cdc, dim_count))
    dims = rng.sample(range(dim_count), cdc)

    for j in dims:
        delta = srd * max(abs(candidate[j]), 1.0)
        if rng.random() < 0.5:
            candidate[j] += delta * rng.random()
        else:
            candidate[j] -= delta * rng.random()
        candidate[j] = max(pos_min, min(pos_max, candidate[j]))

    return candidate


def seeking_step(
    position: Sequence[float],
    instance: KnapsackInstance,
    config: Dict,
    rng: random.Random
) -> Tuple[List[float], List[int], float, float, bool]:
    smp = int(config.get("smp", 5))
    srd = float(config.get("srd", 0.2))
    cdc = int(config.get("cdc", 3))
    pos_min = float(config.get("pos_min", -5.12))
    pos_max = float(config.get("pos_max", 5.12))

    best_position = list(position)
    best_bits, best_value, best_weight, best_feasible = evaluate_position(best_position, instance)

    for _ in range(smp):
        candidate = generate_candidate(position, cdc, srd, rng, pos_min, pos_max)
        bits, value, weight, feasible = evaluate_position(candidate, instance)
        if value > best_value:
            best_position, best_bits, best_value, best_weight, best_feasible = candidate, bits, value, weight, feasible

    return best_position, best_bits, best_value, best_weight, best_feasible