from __future__ import annotations

from copy import deepcopy
from typing import Dict, List, Tuple

DEFAULT_GA_CONFIG: Dict = {
    "population_size": 100,
    "generations": 200,
    "crossover_rate": 0.8,
    "mutation_rate": 0.01,
    "selection": "tournament",
    "crossover": "two_point",
    "mutation": "bit_flip",
    "elitism_count": 2,
    "use_delta_stop": False,
    "delta_generations": 20,
    "delta_min_improvement": 1e-6,
}

DEFAULT_CSO_CONFIG: Dict = {
    "num_cats": 50,
    "max_iter": 200,
    "mr": 0.2,
    "smp": 5,
    "srd": 0.2,
    "cdc": 3,
    "c1": 0.5,
    "vmin": -2.0,
    "vmax": 2.0,
    "pos_min": -5.12,
    "pos_max": 5.12,
    "use_delta_stop": False,
    "delta_iterations": 20,
    "delta_min_improvement": 1e-6,
}


def get_ga_scenarios() -> Dict[str, List[Tuple[str, Dict]]]:
    base = deepcopy(DEFAULT_GA_CONFIG)
    return {
        "GA: Budget (pop x gen)": [
            ("pop20/gen1000", {**deepcopy(base), "population_size": 20,  "generations": 1000}),
            ("pop50/gen400",  {**deepcopy(base), "population_size": 50,  "generations": 400}),
            ("pop100/gen200", {**deepcopy(base), "population_size": 100, "generations": 200}),
            ("pop200/gen100", {**deepcopy(base), "population_size": 200, "generations": 100}),
        ],
        "GA: Crossover rate": [
            ("cr=0.6",  {**deepcopy(base), "crossover_rate": 0.6}),
            ("cr=0.8",  {**deepcopy(base), "crossover_rate": 0.8}),
            ("cr=0.95", {**deepcopy(base), "crossover_rate": 0.95}),
        ],
        "GA: Mutation rate": [
            ("mr=0.01", {**deepcopy(base), "mutation_rate": 0.01}),
            ("mr=0.03", {**deepcopy(base), "mutation_rate": 0.03}),
            ("mr=0.05", {**deepcopy(base), "mutation_rate": 0.05}),
        ],
        "GA: Selection method": [
            ("Roulette",   {**deepcopy(base), "selection": "roulette"}),
            ("Tournament", {**deepcopy(base), "selection": "tournament"}),
            ("Rank",       {**deepcopy(base), "selection": "rank"}),
        ],
        "GA: Crossover method": [
            ("One-point", {**deepcopy(base), "crossover": "one_point"}),
            ("Two-point", {**deepcopy(base), "crossover": "two_point"}),
            ("Uniform",   {**deepcopy(base), "crossover": "uniform"}),
        ],
        "GA: Mutation method": [
            ("Bit-flip",  {**deepcopy(base), "mutation": "bit_flip",  "mutation_rate": 0.01}),
            ("Swap",      {**deepcopy(base), "mutation": "swap",      "mutation_rate": 0.01}),
            ("Inversion", {**deepcopy(base), "mutation": "inversion", "mutation_rate": 0.01}),
        ],
        # Tách riêng elitism vs delta_stop để so sánh công bằng
        "GA: Elitism count": [
            ("Elitism=0", {**deepcopy(base), "elitism_count": 0}),
            ("Elitism=1", {**deepcopy(base), "elitism_count": 1}),
            ("Elitism=2", {**deepcopy(base), "elitism_count": 2}),
            ("Elitism=5", {**deepcopy(base), "elitism_count": 5}),
        ],
        "GA: Early stopping": [
            ("No stop",       {**deepcopy(base), "use_delta_stop": False}),
            ("Delta stop=10", {**deepcopy(base), "use_delta_stop": True, "delta_generations": 10}),
            ("Delta stop=20", {**deepcopy(base), "use_delta_stop": True, "delta_generations": 20}),
            ("Delta stop=30", {**deepcopy(base), "use_delta_stop": True, "delta_generations": 30}),
        ],
    }


def get_cso_scenarios() -> Dict[str, List[Tuple[str, Dict]]]:
    base = deepcopy(DEFAULT_CSO_CONFIG)
    return {
        "CSO: Budget (cats x iter)": [
            ("cats20/iter500",  {**deepcopy(base), "num_cats": 20,  "max_iter": 500}),
            ("cats50/iter200",  {**deepcopy(base), "num_cats": 50,  "max_iter": 200}),
            ("cats100/iter100", {**deepcopy(base), "num_cats": 100, "max_iter": 100}),
            ("cats200/iter50",  {**deepcopy(base), "num_cats": 200, "max_iter": 50}),
        ],
        "CSO: Mixture ratio (MR)": [
            ("MR=0.1", {**deepcopy(base), "mr": 0.1}),
            ("MR=0.2", {**deepcopy(base), "mr": 0.2}),
            ("MR=0.4", {**deepcopy(base), "mr": 0.4}),
            ("MR=0.6", {**deepcopy(base), "mr": 0.6}),
        ],
        "CSO: Seeking Memory Pool (SMP)": [
            ("SMP=3",  {**deepcopy(base), "smp": 3}),
            ("SMP=5",  {**deepcopy(base), "smp": 5}),
            ("SMP=7",  {**deepcopy(base), "smp": 7}),
            ("SMP=10", {**deepcopy(base), "smp": 10}),
        ],
        "CSO: Seeking Range (SRD)": [
            ("SRD=0.1", {**deepcopy(base), "srd": 0.1}),
            ("SRD=0.2", {**deepcopy(base), "srd": 0.2}),
            ("SRD=0.4", {**deepcopy(base), "srd": 0.4}),
        ],
        "CSO: Dimension count (CDC)": [
            ("CDC=1", {**deepcopy(base), "cdc": 1}),
            ("CDC=3", {**deepcopy(base), "cdc": 3}),
            ("CDC=5", {**deepcopy(base), "cdc": 5}),
        ],
        # Thêm so sánh c1 — tham số tracing quan trọng bị thiếu trước đây
        "CSO: Acceleration (c1)": [
            ("c1=0.3", {**deepcopy(base), "c1": 0.3}),
            ("c1=0.5", {**deepcopy(base), "c1": 0.5}),
            ("c1=1.0", {**deepcopy(base), "c1": 1.0}),
            ("c1=2.0", {**deepcopy(base), "c1": 2.0}),
        ],
        "CSO: Early stopping": [
            ("No stop",       {**deepcopy(base), "use_delta_stop": False}),
            ("Delta stop=10", {**deepcopy(base), "use_delta_stop": True, "delta_iterations": 10}),
            ("Delta stop=20", {**deepcopy(base), "use_delta_stop": True, "delta_iterations": 20}),
            ("Delta stop=30", {**deepcopy(base), "use_delta_stop": True, "delta_iterations": 30}),
        ],
    }


def get_scenarios() -> Dict[str, List[Tuple[str, Dict]]]:
    merged: Dict[str, List[Tuple[str, Dict]]] = {}
    merged.update(get_ga_scenarios())
    merged.update(get_cso_scenarios())
    return merged