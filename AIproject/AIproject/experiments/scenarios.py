from __future__ import annotations

from copy import deepcopy
from typing import Dict, List, Tuple

# ------------------------------------------------------------
# Defaults
# ------------------------------------------------------------
# Theo yêu cầu thầy:
# - mutation_rate của GA phải <= 0.05
# - so sánh nội bộ phải công bằng:
#   giữ budget tính toán gần tương đương giữa các case
#   GA: population_size * generations
#   CSO: num_cats * max_iter
# ------------------------------------------------------------

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

    # Budget gần như giữ cố định: pop * generations ~= 20,000
    ga_budget = [
        ("GA-pop20-gen1000", {**deepcopy(base), "population_size": 20, "generations": 1000}),
        ("GA-pop50-gen400", {**deepcopy(base), "population_size": 50, "generations": 400}),
        ("GA-pop100-gen200", {**deepcopy(base), "population_size": 100, "generations": 200}),
        ("GA-pop200-gen100", {**deepcopy(base), "population_size": 200, "generations": 100}),
    ]

    return {
        "ga_budget_population_generation": ga_budget,

        "ga_hyper_crossover": [
            ("GA-cr-0.6", {**deepcopy(base), "crossover_rate": 0.6}),
            ("GA-cr-0.8", {**deepcopy(base), "crossover_rate": 0.8}),
            ("GA-cr-0.95", {**deepcopy(base), "crossover_rate": 0.95}),
        ],

        "ga_hyper_mutation": [
            ("GA-mr-0.01", {**deepcopy(base), "mutation_rate": 0.01}),
            ("GA-mr-0.03", {**deepcopy(base), "mutation_rate": 0.03}),
            ("GA-mr-0.05", {**deepcopy(base), "mutation_rate": 0.05}),
        ],

        "ga_operator_selection": [
            ("GA-sel-roulette", {**deepcopy(base), "selection": "roulette"}),
            ("GA-sel-tournament", {**deepcopy(base), "selection": "tournament"}),
            ("GA-sel-rank", {**deepcopy(base), "selection": "rank"}),
        ],

        "ga_operator_crossover": [
            ("GA-cross-one_point", {**deepcopy(base), "crossover": "one_point"}),
            ("GA-cross-two_point", {**deepcopy(base), "crossover": "two_point"}),
            ("GA-cross-uniform", {**deepcopy(base), "crossover": "uniform"}),
        ],

        "ga_operator_mutation": [
            ("GA-mut-bit_flip", {**deepcopy(base), "mutation": "bit_flip", "mutation_rate": 0.01}),
            ("GA-mut-swap", {**deepcopy(base), "mutation": "swap", "mutation_rate": 0.01}),
            ("GA-mut-inversion", {**deepcopy(base), "mutation": "inversion", "mutation_rate": 0.01}),
        ],

        "ga_preservation": [
            ("GA-no-elitism", {**deepcopy(base), "elitism_count": 0, "use_delta_stop": False}),
            ("GA-elitism-1", {**deepcopy(base), "elitism_count": 1, "use_delta_stop": False}),
            ("GA-elitism-5", {**deepcopy(base), "elitism_count": 5, "use_delta_stop": False}),
            ("GA-delta-10", {**deepcopy(base), "elitism_count": 2, "use_delta_stop": True, "delta_generations": 10}),
            ("GA-delta-20", {**deepcopy(base), "elitism_count": 2, "use_delta_stop": True, "delta_generations": 20}),
        ],
    }


def get_cso_scenarios() -> Dict[str, List[Tuple[str, Dict]]]:
    base = deepcopy(DEFAULT_CSO_CONFIG)

    # Budget gần như giữ cố định: num_cats * max_iter ~= 10,000
    cso_budget = [
        ("CSO-cats20-iter500", {**deepcopy(base), "num_cats": 20, "max_iter": 500}),
        ("CSO-cats50-iter200", {**deepcopy(base), "num_cats": 50, "max_iter": 200}),
        ("CSO-cats100-iter100", {**deepcopy(base), "num_cats": 100, "max_iter": 100}),
        ("CSO-cats200-iter50", {**deepcopy(base), "num_cats": 200, "max_iter": 50}),
    ]

    return {
        "cso_budget_numcats_iterations": cso_budget,

        "cso_hyper_mr": [
            ("CSO-mr-0.1", {**deepcopy(base), "mr": 0.1}),
            ("CSO-mr-0.2", {**deepcopy(base), "mr": 0.2}),
            ("CSO-mr-0.4", {**deepcopy(base), "mr": 0.4}),
            ("CSO-mr-0.6", {**deepcopy(base), "mr": 0.6}),
        ],

        "cso_hyper_smp": [
            ("CSO-smp-3", {**deepcopy(base), "smp": 3}),
            ("CSO-smp-5", {**deepcopy(base), "smp": 5}),
            ("CSO-smp-7", {**deepcopy(base), "smp": 7}),
            ("CSO-smp-10", {**deepcopy(base), "smp": 10}),
        ],

        "cso_hyper_srd": [
            ("CSO-srd-0.1", {**deepcopy(base), "srd": 0.1}),
            ("CSO-srd-0.2", {**deepcopy(base), "srd": 0.2}),
            ("CSO-srd-0.4", {**deepcopy(base), "srd": 0.4}),
        ],

        "cso_hyper_cdc": [
            ("CSO-cdc-1", {**deepcopy(base), "cdc": 1}),
            ("CSO-cdc-3", {**deepcopy(base), "cdc": 3}),
            ("CSO-cdc-5", {**deepcopy(base), "cdc": 5}),
        ],

        "cso_preservation": [
            ("CSO-no-delta", {**deepcopy(base), "use_delta_stop": False}),
            ("CSO-delta-10", {**deepcopy(base), "use_delta_stop": True, "delta_iterations": 10}),
            ("CSO-delta-20", {**deepcopy(base), "use_delta_stop": True, "delta_iterations": 20}),
        ],
    }


def get_scenarios() -> Dict[str, List[Tuple[str, Dict]]]:
    merged: Dict[str, List[Tuple[str, Dict]]] = {}
    merged.update(get_ga_scenarios())
    merged.update(get_cso_scenarios())
    return merged