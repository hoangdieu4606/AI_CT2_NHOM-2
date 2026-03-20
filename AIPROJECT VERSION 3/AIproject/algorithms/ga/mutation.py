from __future__ import annotations

import random
from typing import List


def bit_flip_mutation(chromosome: List[int], mutation_rate: float, rng: random.Random) -> List[int]:
    mutated = chromosome[:]
    for i in range(len(mutated)):
        if rng.random() < mutation_rate:
            mutated[i] = 1 - mutated[i]
    return mutated


def swap_mutation(chromosome: List[int], mutation_rate: float, rng: random.Random) -> List[int]:
    mutated = chromosome[:]
    if len(mutated) >= 2 and rng.random() < mutation_rate:
        i, j = rng.sample(range(len(mutated)), 2)
        mutated[i], mutated[j] = mutated[j], mutated[i]
    return mutated


def inversion_mutation(chromosome: List[int], mutation_rate: float, rng: random.Random) -> List[int]:
    mutated = chromosome[:]
    if len(mutated) >= 2 and rng.random() < mutation_rate:
        i, j = sorted(rng.sample(range(len(mutated)), 2))
        mutated[i:j + 1] = list(reversed(mutated[i:j + 1]))
    return mutated


def apply_mutation(chromosome: List[int], mutation_method: str, mutation_rate: float, rng: random.Random) -> List[int]:
    mutation_method = mutation_method.lower()
    if mutation_method == "swap":
        return swap_mutation(chromosome, mutation_rate, rng)
    if mutation_method == "inversion":
        return inversion_mutation(chromosome, mutation_rate, rng)
    return bit_flip_mutation(chromosome, mutation_rate, rng)