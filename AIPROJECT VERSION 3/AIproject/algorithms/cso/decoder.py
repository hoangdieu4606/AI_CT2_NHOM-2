from typing import Iterable, List, Tuple
from core.models import KnapsackInstance
from core.fitness import evaluate_solution


def decode_priority_to_knapsack(position: Iterable[float], instance: KnapsackInstance) -> List[int]:
    """
    Convert continuous CSO position -> binary knapsack solution
    """
    order = sorted(range(len(instance.items)), key=lambda i: list(position)[i], reverse=True)

    bits = [0] * len(instance.items)
    current_weight = 0.0

    for idx in order:
        item = instance.items[idx]

        if current_weight + item.weight <= instance.capacity:
            bits[idx] = 1
            current_weight += item.weight

    return bits


def evaluate_position(position: Iterable[float], instance: KnapsackInstance) -> Tuple[List[int], float, float, bool]:

    bits = decode_priority_to_knapsack(position, instance)

    value, weight, feasible = evaluate_solution(bits, instance)

    return bits, value, weight, feasible