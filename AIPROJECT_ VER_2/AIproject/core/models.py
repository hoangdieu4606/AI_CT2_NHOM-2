from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Item:
    id: int
    weight: float
    value: float
    priority: int = 1


@dataclass
class KnapsackInstance:
    items: List[Item]
    capacity: float
    difficulty: str = "random"
    name: str = "Unnamed Instance"


@dataclass
class OptimizationResult:
    algorithm: str
    best_solution: List[int]
    best_value: float
    best_weight: float
    is_feasible: bool
    runtime_sec: float
    history_best: List[float] = field(default_factory=list)
    history_avg: List[float] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)