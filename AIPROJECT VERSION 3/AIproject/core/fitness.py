from typing import Iterable, List, Tuple

from core.models import KnapsackInstance


def compute_weight(solution: Iterable[int], instance: KnapsackInstance) -> float:
    return sum(gene * item.weight for gene, item in zip(solution, instance.items))


def compute_value(solution: Iterable[int], instance: KnapsackInstance) -> float:
    return sum(gene * item.value for gene, item in zip(solution, instance.items))


def evaluate_solution(solution: List[int], instance: KnapsackInstance) -> Tuple[float, float, bool]:
    """
    Policy theo yêu cầu thầy:
    - Nếu vượt capacity thì fitness/value = 0
    - Không repair trong quá trình đánh giá
    """
    total_weight = compute_weight(solution, instance)
    total_value = compute_value(solution, instance)
    feasible = total_weight <= instance.capacity + 1e-9

    if not feasible:
        total_value = 0.0

    return total_value, total_weight, feasible