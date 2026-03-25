from __future__ import annotations

import random
import time
from typing import Dict, List, Sequence

from algorithms.ga.crossover import apply_crossover
from algorithms.ga.mutation import apply_mutation
from algorithms.ga.population import initialize_population
from algorithms.ga.selection import select_parent
from core.fitness import evaluate_solution
from core.models import KnapsackInstance, OptimizationResult


def _evaluate_population(population: Sequence[List[int]], instance: KnapsackInstance):
    values, weights, feasible_flags = [], [], []
    for individual in population:
        val, wt, feasible = evaluate_solution(individual, instance)
        values.append(val)
        weights.append(wt)
        feasible_flags.append(feasible)
    return values, weights, feasible_flags


def solve(instance: KnapsackInstance, config: Dict | None = None, seed: int = 42) -> OptimizationResult:
    config = config or {}
    rng = random.Random(seed)

    population_size = int(config.get("population_size", 100))
    generations = int(config.get("generations", 200))
    crossover_rate = float(config.get("crossover_rate", 0.8))
    mutation_rate = float(config.get("mutation_rate", 0.01))
    selection_method = str(config.get("selection", "tournament"))
    crossover_method = str(config.get("crossover", "two_point"))
    mutation_method = str(config.get("mutation", "bit_flip"))
    elitism_count = int(config.get("elitism_count", 2))
    tournament_size = int(config.get("tournament_size", 3))
    use_delta_stop = bool(config.get("use_delta_stop", False))
    delta_generations = int(config.get("delta_generations", 20))
    delta_min_improvement = float(config.get("delta_min_improvement", 1e-6))

    start_time = time.perf_counter()

    population = initialize_population(instance, population_size, rng)
    history_best: List[float] = []
    history_avg: List[float] = []

    best_solution = population[0][:]
    best_value, best_weight, best_feasible = evaluate_solution(best_solution, instance)

    stagnant = 0

    for generation in range(generations):
        fitnesses, weights, feasible_flags = _evaluate_population(population, instance)
        gen_best_idx = max(range(len(population)), key=lambda i: fitnesses[i])
        gen_best_value = fitnesses[gen_best_idx]

        history_best.append(gen_best_value)
        history_avg.append(sum(fitnesses) / len(fitnesses))

        if gen_best_value > best_value + 1e-12:
            best_solution = population[gen_best_idx][:]
            best_value = fitnesses[gen_best_idx]
            best_weight = weights[gen_best_idx]
            best_feasible = feasible_flags[gen_best_idx]
            stagnant = 0
        else:
            stagnant += 1

        if use_delta_stop and generation >= delta_generations and stagnant >= delta_generations:
            recent_best = max(history_best[-delta_generations:])
            old_best = max(history_best[-2 * delta_generations:-delta_generations], default=history_best[0])
            if recent_best - old_best < delta_min_improvement:
                break

        elite_indices = sorted(range(len(population)), key=lambda i: fitnesses[i], reverse=True)[:max(0, elitism_count)]
        next_population = [population[i][:] for i in elite_indices]

        while len(next_population) < population_size:
            parent1 = select_parent(population, fitnesses, selection_method, rng, tournament_size)
            parent2 = select_parent(population, fitnesses, selection_method, rng, tournament_size)

            child1, child2 = apply_crossover(parent1, parent2, crossover_method, crossover_rate, rng)
            child1 = apply_mutation(child1, mutation_method, mutation_rate, rng)
            child2 = apply_mutation(child2, mutation_method, mutation_rate, rng)

            next_population.append(child1)
            if len(next_population) < population_size:
                next_population.append(child2)

        population = next_population

    runtime = time.perf_counter() - start_time
    return OptimizationResult(
        algorithm="GA",
        best_solution=best_solution,
        best_value=best_value,
        best_weight=best_weight,
        is_feasible=best_feasible,
        runtime_sec=runtime,
        history_best=history_best,
        history_avg=history_avg,
        meta={
            "config": {
                "population_size": population_size,
                "generations": generations,
                "crossover_rate": crossover_rate,
                "mutation_rate": mutation_rate,
                "selection": selection_method,
                "crossover": crossover_method,
                "mutation": mutation_method,
                "elitism_count": elitism_count,
                "use_delta_stop": use_delta_stop,
                "delta_generations": delta_generations,
            }
        }
    )
