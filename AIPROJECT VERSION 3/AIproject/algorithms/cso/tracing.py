from __future__ import annotations

import random
from typing import Dict, List, Sequence


def tracing_step(
    position: Sequence[float],
    velocity: Sequence[float],
    gbest_position: Sequence[float],
    config: Dict,
    rng: random.Random
) -> tuple[List[float], List[float]]:
    c1 = float(config.get("c1", 0.5))
    vmin = float(config.get("vmin", -2.0))
    vmax = float(config.get("vmax", 2.0))
    pos_min = float(config.get("pos_min", -5.12))
    pos_max = float(config.get("pos_max", 5.12))

    new_velocity = list(velocity)
    new_position = list(position)

    for j in range(len(new_position)):
        new_velocity[j] = new_velocity[j] + rng.random() * c1 * (gbest_position[j] - new_position[j])
        new_velocity[j] = max(vmin, min(vmax, new_velocity[j]))
        new_position[j] = new_position[j] + new_velocity[j]
        new_position[j] = max(pos_min, min(pos_max, new_position[j]))

    return new_position, new_velocity