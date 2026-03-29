from __future__ import annotations

import random
from typing import List, Tuple


def one_point_crossover(parent1: List[int], parent2: List[int], rng: random.Random) -> Tuple[List[int], List[int]]:
    if len(parent1) < 2:
        return parent1[:], parent2[:]
    point = rng.randint(1, len(parent1) - 1)
    child1 = parent1[:point] + parent2[point:]
    child2 = parent2[:point] + parent1[point:]
    return child1, child2


def two_point_crossover(parent1: List[int], parent2: List[int], rng: random.Random) -> Tuple[List[int], List[int]]:
    if len(parent1) < 3:
        return one_point_crossover(parent1, parent2, rng)
    i, j = sorted(rng.sample(range(1, len(parent1)), 2))
    child1 = parent1[:i] + parent2[i:j] + parent1[j:]
    child2 = parent2[:i] + parent1[i:j] + parent2[j:]
    return child1, child2


def uniform_crossover(parent1: List[int], parent2: List[int], rng: random.Random) -> Tuple[List[int], List[int]]:
    child1, child2 = [], []
    for a, b in zip(parent1, parent2):
        if rng.random() < 0.5:
            child1.append(a)
            child2.append(b)
        else:
            child1.append(b)
            child2.append(a)
    return child1, child2


def apply_crossover(parent1: List[int], parent2: List[int], crossover_method: str, crossover_rate: float, rng: random.Random) -> Tuple[List[int], List[int]]:
    if rng.random() > crossover_rate:
        return parent1[:], parent2[:]

    method = crossover_method.lower()
    if method == "one_point":
        return one_point_crossover(parent1, parent2, rng)
    if method == "uniform":
        return uniform_crossover(parent1, parent2, rng)
    return two_point_crossover(parent1, parent2, rng)