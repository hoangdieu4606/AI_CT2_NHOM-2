from core.datasets import generate_easy_problem
from experiments.benchmark import run_benchmark_in_memory

instance = generate_easy_problem(n_items=30, seed=42)

scenarios = [
    "ga_operator_selection",
    "ga_operator_crossover",
    "ga_operator_mutation",
    "ga_preservation"
]

for scenario in scenarios:
    print("\n==============================", flush=True)
    print("Running scenario:", scenario, flush=True)
    print("==============================", flush=True)

    report = run_benchmark_in_memory(
        instance,
        scenario_key=scenario,
        n_runs=3,      # test nhanh trước
        seed_base=100
    )

    print("Done scenario:", scenario, flush=True)

    for case in report["cases"]:
        print(
            f"{case['case_name']:25s} | "
            f"mean={case['value']['mean']:.2f} | "
            f"std={case['value']['std']:.2f} | "
            f"runtime={case['runtime']['mean']:.4f}s",
            flush=True
        )