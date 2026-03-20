from __future__ import annotations

import random
from typing import List

from core.models import Item, KnapsackInstance


def _build_instance(items: List[Item], capacity_ratio: float, difficulty: str, name: str) -> KnapsackInstance:
    total_weight = sum(item.weight for item in items)
    capacity = round(total_weight * capacity_ratio, 2)
    return KnapsackInstance(items=items, capacity=capacity, difficulty=difficulty, name=name)


def generate_easy_problem(n_items: int = 30, seed: int | None = None) -> KnapsackInstance:
    rng = random.Random(seed)
    items = []
    for i in range(n_items):
        weight = rng.randint(2, 16)
        ratio = rng.uniform(2.5, 4.5)
        value = round(weight * ratio + rng.uniform(3, 10), 2)
        priority = rng.randint(2, 5)
        items.append(Item(id=i + 1, weight=float(weight), value=value, priority=priority))
    return _build_instance(items, capacity_ratio=0.58, difficulty="easy", name=f"Easy-{n_items}")


def generate_hard_problem(n_items: int = 30, seed: int | None = None) -> KnapsackInstance:
    rng = random.Random(seed)
    items = []
    for i in range(n_items):
        weight = rng.randint(5, 35)
        value = round(weight + rng.uniform(0.0, 8.0), 2)
        if rng.random() < 0.12:
            value = round(value * rng.uniform(1.4, 1.9), 2)
        priority = rng.randint(1, 5)
        items.append(Item(id=i + 1, weight=float(weight), value=value, priority=priority))
    return _build_instance(items, capacity_ratio=0.30, difficulty="hard", name=f"Hard-{n_items}")


def generate_problem_random(n_items: int = 30, seed: int | None = None) -> KnapsackInstance:
    rng = random.Random(seed)
    items = []
    for i in range(n_items):
        weight = rng.randint(1, 25)
        value = round(rng.uniform(5, 70), 2)
        priority = rng.randint(1, 5)
        items.append(Item(id=i + 1, weight=float(weight), value=value, priority=priority))
    capacity_ratio = rng.uniform(0.32, 0.55)
    return _build_instance(items, capacity_ratio=capacity_ratio, difficulty="random", name=f"Random-{n_items}")