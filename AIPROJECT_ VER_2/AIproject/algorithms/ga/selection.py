from __future__ import annotations

import random
from typing import List, Sequence


def tournament_selection(population: Sequence[List[int]], fitnesses: Sequence[float], rng: random.Random, tournament_size: int = 3) -> List[int]:
    size = min(tournament_size, len(population))
    indices = rng.sample(range(len(population)), size)
    best_idx = max(indices, key=lambda idx: fitnesses[idx])
    return population[best_idx][:]


def roulette_selection(population: Sequence[List[int]], fitnesses: Sequence[float], rng: random.Random) -> List[int]:
    min_fit = min(fitnesses)
    shifted = [f - min_fit + 1e-6 for f in fitnesses]
    total = sum(shifted)
    pick = rng.random() * total
    cumulative = 0.0
    for individual, fit in zip(population, shifted):
        cumulative += fit
        if cumulative >= pick:
            return individual[:]
    return population[-1][:]


def rank_selection(population: Sequence[List[int]], fitnesses: Sequence[float], rng: random.Random) -> List[int]:
    ranked = sorted(range(len(population)), key=lambda i: fitnesses[i])
    weights = list(range(1, len(population) + 1))
    total = sum(weights)
    pick = rng.random() * total
    cumulative = 0
    for rank_pos, idx in enumerate(ranked):
        cumulative += weights[rank_pos]
        if cumulative >= pick:
            return population[idx][:]
    return population[ranked[-1]][:]


def select_parent(population: Sequence[List[int]], fitnesses: Sequence[float], selection_method: str, rng: random.Random, tournament_size: int = 3) -> List[int]:
    selection_method = selection_method.lower()
    if selection_method == "roulette":
        return roulette_selection(population, fitnesses, rng)
    if selection_method == "rank":
        return rank_selection(population, fitnesses, rng)
    return tournament_selection(population, fitnesses, rng, tournament_size=tournament_size)