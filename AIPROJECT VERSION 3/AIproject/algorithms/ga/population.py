from __future__ import annotations

import random
from typing import List

from core.models import KnapsackInstance


def create_random_individual(instance: KnapsackInstance, rng: random.Random) -> List[int]:
    # Theo yêu cầu thầy: không repair cá thể vi phạm
    return [1 if rng.random() < 0.5 else 0 for _ in instance.items]


def initialize_population(instance: KnapsackInstance, population_size: int, rng: random.Random) -> List[List[int]]:
    return [create_random_individual(instance, rng) for _ in range(population_size)]