from __future__ import annotations

import queue
import threading
import traceback
import tkinter as tk
from tkinter import messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from algorithms.cso.cso_solver import solve as solve_cso
from algorithms.ga.ga_solver import solve as solve_ga
from core.datasets import generate_easy_problem, generate_hard_problem, generate_problem_random
from core.models import KnapsackInstance, OptimizationResult
from experiments.benchmark import run_benchmark_in_memory
from experiments.scenarios import DEFAULT_CSO_CONFIG, DEFAULT_GA_CONFIG, get_scenarios
from gui.widgets.truck_canvas import TruckCanvas


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Logistics Optimizer - Knapsack (GA vs CSO)")
        self.geometry("1380x860")
        self.minsize(1200, 760)

        self.instance: KnapsackInstance = generate_easy_problem(30, seed=42)
        self.last_result: OptimizationResult | None = None

        self.task_queue: queue.Queue = queue.Queue()
        self.status_var = tk.StringVar(value="Sẵn sàng.")
        self._build_layout()
        self._load_instance_to_table(self.instance)
        self.after(150, self._poll_queue)

    def _build_layout(self):
        header = ttk.Frame(self, padding=10)
        header.pack(side="top", fill="x")

        title = ttk.Label(
            header,
            text="Tối ưu hóa vận tải & kho bãi bằng GA và CSO",
            font=("Segoe UI", 18, "bold")
        )
        title.pack(side="left")

        ttk.Label(
            header,
            textvariable=self.status_var,
            foreground="#0a58ca",
            font=("Segoe UI", 10, "italic")
        ).pack(side="right")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.data_tab = ttk.Frame(self.notebook)
        self.ga_tab = ttk.Frame(self.notebook)
        self.cso_tab = ttk.Frame(self.notebook)
        self.compare_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.data_tab, text="Dữ liệu & Mô phỏng")
        self.notebook.add(self.ga_tab, text="Genetic Algorithm")
        self.notebook.add(self.cso_tab, text="Cat Swarm Optimization")
        self.notebook.add(self.compare_tab, text="So sánh Benchmark")

        self._build_data_tab()
        self._build_ga_tab()
        self._build_cso_tab()
        self._build_compare_tab()

    def _build_data_tab(self):
        left = ttk.Frame(self.data_tab, padding=10)
        left.pack(side="left", fill="y")
        right = ttk.Frame(self.data_tab, padding=10)
        right.pack(side="right", fill="both", expand=True)

        ttk.Label(left, text="Sinh bộ dữ liệu kiện hàng", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))

        self.data_n_items = tk.IntVar(value=30)
        self.data_seed = tk.IntVar(value=42)

        row = ttk.Frame(left)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Số kiện hàng", width=18).pack(side="left")
        ttk.Entry(row, textvariable=self.data_n_items, width=10).pack(side="left")

        row = ttk.Frame(left)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Seed", width=18).pack(side="left")
        ttk.Entry(row, textvariable=self.data_seed, width=10).pack(side="left")

        btn_frame = ttk.Frame(left)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="Sinh Easy", command=lambda: self._generate_instance("easy")).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Sinh Hard", command=lambda: self._generate_instance("hard")).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Sinh Random", command=lambda: self._generate_instance("random")).pack(fill="x", pady=2)

        self.instance_info = tk.Text(left, height=8, width=40, wrap="word")
        self.instance_info.pack(fill="x", pady=(12, 0))

        table_frame = ttk.LabelFrame(right, text="Danh sách kiện hàng", padding=8)
        table_frame.pack(fill="both", expand=True)

        columns = ("id", "weight", "value", "priority", "ratio")
        self.item_table = ttk.Treeview(table_frame, columns=columns, show="headings", height=16)

        headings = {
            "id": "ID",
            "weight": "Khối lượng",
            "value": "Giá trị/Cước phí",
            "priority": "Ưu tiên",
            "ratio": "Value/Weight"
        }
        widths = {"id": 60, "weight": 110, "value": 140, "priority": 90, "ratio": 110}

        for col in columns:
            self.item_table.heading(col, text=headings[col])
            self.item_table.column(col, width=widths[col], anchor="center")

        self.item_table.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.item_table.yview)
        scrollbar.pack(side="right", fill="y")
        self.item_table.configure(yscrollcommand=scrollbar.set)

        viz_frame = ttk.LabelFrame(right, text="Xe tải & kiện hàng được chọn", padding=8)
        viz_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.truck_canvas = TruckCanvas(viz_frame, height=380)
        self.truck_canvas.pack(fill="both", expand=True)

    def _build_ga_tab(self):
        left = ttk.Frame(self.ga_tab, padding=10)
        left.pack(side="left", fill="y")
        right = ttk.Frame(self.ga_tab, padding=10)
        right.pack(side="right", fill="both", expand=True)

        self.ga_vars = {
            "population_size": tk.IntVar(value=DEFAULT_GA_CONFIG["population_size"]),
            "generations": tk.IntVar(value=DEFAULT_GA_CONFIG["generations"]),
            "crossover_rate": tk.DoubleVar(value=DEFAULT_GA_CONFIG["crossover_rate"]),
            "mutation_rate": tk.DoubleVar(value=DEFAULT_GA_CONFIG["mutation_rate"]),
            "selection": tk.StringVar(value=DEFAULT_GA_CONFIG["selection"]),
            "crossover": tk.StringVar(value=DEFAULT_GA_CONFIG["crossover"]),
            "mutation": tk.StringVar(value=DEFAULT_GA_CONFIG["mutation"]),
            "elitism_count": tk.IntVar(value=DEFAULT_GA_CONFIG["elitism_count"]),
            "use_delta_stop": tk.BooleanVar(value=DEFAULT_GA_CONFIG["use_delta_stop"]),
            "delta_generations": tk.IntVar(value=DEFAULT_GA_CONFIG["delta_generations"]),
            "delta_min_improvement": tk.DoubleVar(value=DEFAULT_GA_CONFIG["delta_min_improvement"]),
            "seed": tk.IntVar(value=42),
        }

        ttk.Label(left, text="Cấu hình GA", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))

        fields = [
            ("population_size", "Kích thước quần thể"),
            ("generations", "Số thế hệ"),
            ("crossover_rate", "Tỉ lệ lai tạo"),
            ("mutation_rate", "Tỉ lệ đột biến"),
            ("elitism_count", "Elitism count"),
            ("delta_generations", "Delta generations"),
            ("delta_min_improvement", "Delta min improvement"),
            ("seed", "Seed"),
        ]

        for key, label in fields:
            row = ttk.Frame(left)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label, width=20).pack(side="left")
            ttk.Entry(row, textvariable=self.ga_vars[key], width=12).pack(side="left")

        self._add_combo(left, "selection", "Chọn lọc", ["roulette", "tournament", "rank"])
        self._add_combo(left, "crossover", "Lai tạo", ["one_point", "two_point", "uniform"])
        self._add_combo(left, "mutation", "Đột biến", ["bit_flip", "swap", "inversion"])

        ttk.Checkbutton(left, text="Bật delta stop", variable=self.ga_vars["use_delta_stop"]).pack(anchor="w", pady=8)
        ttk.Button(left, text="Chạy GA", command=self._run_ga).pack(fill="x", pady=8)

        summary = ttk.LabelFrame(left, text="Kết quả GA", padding=8)
        summary.pack(fill="x", pady=(10, 0))
        self.ga_summary = tk.Text(summary, width=42, height=10, wrap="word")
        self.ga_summary.pack(fill="both", expand=True)

        charts = ttk.Frame(right)
        charts.pack(fill="both", expand=True)

        self.ga_fig = Figure(figsize=(8, 5), dpi=100)
        self.ga_ax = self.ga_fig.add_subplot(111)
        self.ga_canvas = FigureCanvasTkAgg(self.ga_fig, master=charts)
        self.ga_canvas.get_tk_widget().pack(fill="both", expand=True)

    def _build_cso_tab(self):
        left = ttk.Frame(self.cso_tab, padding=10)
        left.pack(side="left", fill="y")
        right = ttk.Frame(self.cso_tab, padding=10)
        right.pack(side="right", fill="both", expand=True)

        self.cso_vars = {
            "num_cats": tk.IntVar(value=DEFAULT_CSO_CONFIG["num_cats"]),
            "max_iter": tk.IntVar(value=DEFAULT_CSO_CONFIG["max_iter"]),
            "mr": tk.DoubleVar(value=DEFAULT_CSO_CONFIG["mr"]),
            "smp": tk.IntVar(value=DEFAULT_CSO_CONFIG["smp"]),
            "srd": tk.DoubleVar(value=DEFAULT_CSO_CONFIG["srd"]),
            "cdc": tk.IntVar(value=DEFAULT_CSO_CONFIG["cdc"]),
            "c1": tk.DoubleVar(value=DEFAULT_CSO_CONFIG["c1"]),
            "vmin": tk.DoubleVar(value=DEFAULT_CSO_CONFIG["vmin"]),
            "vmax": tk.DoubleVar(value=DEFAULT_CSO_CONFIG["vmax"]),
            "seed": tk.IntVar(value=42),
        }

        ttk.Label(left, text="Cấu hình CSO", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))

        fields = [
            ("num_cats", "Số lượng cats"),
            ("max_iter", "Số iteration"),
            ("mr", "Mixture ratio (MR)"),
            ("smp", "Seeking Memory Pool"),
            ("srd", "Seeking Range"),
            ("cdc", "Counts of Dimension"),
            ("c1", "Gia tốc c1"),
            ("vmin", "Vmin"),
            ("vmax", "Vmax"),
            ("seed", "Seed"),
        ]

        for key, label in fields:
            row = ttk.Frame(left)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label, width=20).pack(side="left")
            ttk.Entry(row, textvariable=self.cso_vars[key], width=12).pack(side="left")

        ttk.Button(left, text="Chạy CSO", command=self._run_cso).pack(fill="x", pady=8)

        summary = ttk.LabelFrame(left, text="Kết quả CSO", padding=8)
        summary.pack(fill="x", pady=(10, 0))
        self.cso_summary = tk.Text(summary, width=42, height=10, wrap="word")
        self.cso_summary.pack(fill="both", expand=True)

        charts = ttk.Frame(right)
        charts.pack(fill="both", expand=True)

        self.cso_fig = Figure(figsize=(8, 5), dpi=100)
        self.cso_ax = self.cso_fig.add_subplot(111)
        self.cso_canvas = FigureCanvasTkAgg(self.cso_fig, master=charts)
        self.cso_canvas.get_tk_widget().pack(fill="both", expand=True)

    def _build_compare_tab(self):
        left = ttk.Frame(self.compare_tab, padding=10)
        left.pack(side="left", fill="y")
        right = ttk.Frame(self.compare_tab, padding=10)
        right.pack(side="right", fill="both", expand=True)

        self.compare_scenario = tk.StringVar(value="ga_budget_population_generation")
        self.compare_runs = tk.IntVar(value=3)

        ttk.Label(left, text="Thiết lập benchmark", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))

        row = ttk.Frame(left)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text="Scenario", width=18).pack(side="left")
        ttk.Combobox(
            row,
            textvariable=self.compare_scenario,
            values=list(get_scenarios().keys()),
            state="readonly",
            width=24
        ).pack(side="left")

        row = ttk.Frame(left)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text="Số lần chạy", width=18).pack(side="left")
        ttk.Entry(row, textvariable=self.compare_runs, width=10).pack(side="left")

        ttk.Button(left, text="Chạy benchmark", command=self._run_benchmark).pack(fill="x", pady=8)

        summary = ttk.LabelFrame(left, text="Tóm tắt benchmark", padding=8)
        summary.pack(fill="both", expand=True, pady=(10, 0))
        self.compare_summary = tk.Text(summary, width=42, height=22, wrap="word")
        self.compare_summary.pack(fill="both", expand=True)

        charts = ttk.Frame(right)
        charts.pack(fill="both", expand=True)

        self.compare_fig = Figure(figsize=(8, 5), dpi=100)
        self.compare_ax = self.compare_fig.add_subplot(111)
        self.compare_canvas = FigureCanvasTkAgg(self.compare_fig, master=charts)
        self.compare_canvas.get_tk_widget().pack(fill="both", expand=True)

    def _add_combo(self, parent, key, label, values):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=20).pack(side="left")
        ttk.Combobox(row, textvariable=self.ga_vars[key], values=values, state="readonly", width=12).pack(side="left")

    def _set_status(self, text: str):
        self.status_var.set(text)

    def _generate_instance(self, difficulty: str):
        n_items = self.data_n_items.get()
        seed = self.data_seed.get()

        if difficulty == "easy":
            self.instance = generate_easy_problem(n_items, seed=seed)
        elif difficulty == "hard":
            self.instance = generate_hard_problem(n_items, seed=seed)
        else:
            self.instance = generate_problem_random(n_items, seed=seed)

        self.last_result = None
        self._load_instance_to_table(self.instance)
        self.truck_canvas.set_solution(self.instance, None)
        self._set_status(f"Đã sinh dữ liệu {self.instance.name}.")

    def _load_instance_to_table(self, instance: KnapsackInstance):
        for row_id in self.item_table.get_children():
            self.item_table.delete(row_id)

        for item in instance.items:
            ratio = item.value / max(item.weight, 1e-9)
            self.item_table.insert("", "end", values=(item.id, item.weight, item.value, item.priority, round(ratio, 2)))

        total_weight = sum(i.weight for i in instance.items)
        total_value = sum(i.value for i in instance.items)

        text = (
            f"Tên bộ dữ liệu: {instance.name}\n"
            f"Độ khó: {instance.difficulty}\n"
            f"Số kiện hàng: {len(instance.items)}\n"
            f"Tải trọng xe tối đa: {instance.capacity:.2f}\n"
            f"Tổng khối lượng tất cả kiện: {total_weight:.2f}\n"
            f"Tổng giá trị tất cả kiện: {total_value:.2f}\n"
        )
        self.instance_info.delete("1.0", "end")
        self.instance_info.insert("1.0", text)

    def _run_background(self, worker, callback, start_text="Đang chạy..."):
        self._set_status(start_text)

        def task():
            try:
                result = worker()
                self.task_queue.put(("success", callback, result))
            except Exception:
                self.task_queue.put(("error", callback, traceback.format_exc()))

        threading.Thread(target=task, daemon=True).start()

    def _poll_queue(self):
        try:
            while True:
                kind, callback, payload = self.task_queue.get_nowait()
                if kind == "success":
                    callback(payload)
                else:
                    self._set_status("Có lỗi.")
                    messagebox.showerror("Lỗi", payload)
        except queue.Empty:
            pass

        self.after(150, self._poll_queue)

    def _run_ga(self):
        config = {k: v.get() for k, v in self.ga_vars.items() if k != "seed"}
        seed = self.ga_vars["seed"].get()
        self._run_background(
            worker=lambda: solve_ga(self.instance, config, seed=seed),
            callback=self._on_ga_done,
            start_text="GA đang tối ưu..."
        )

    def _run_cso(self):
        config = {k: v.get() for k, v in self.cso_vars.items() if k != "seed"}
        seed = self.cso_vars["seed"].get()
        self._run_background(
            worker=lambda: solve_cso(self.instance, config, seed=seed),
            callback=self._on_cso_done,
            start_text="CSO đang tối ưu..."
        )

    def _run_benchmark(self):
        scenario_key = self.compare_scenario.get()
        n_runs = self.compare_runs.get()
        self._run_background(
            worker=lambda: run_benchmark_in_memory(self.instance, scenario_key=scenario_key, n_runs=n_runs),
            callback=self._on_benchmark_done,
            start_text=f"Đang benchmark scenario '{scenario_key}'..."
        )

    def _format_result_text(self, result: OptimizationResult) -> str:
        selected_ids = [str(self.instance.items[i].id) for i, g in enumerate(result.best_solution) if g == 1]
        return (
            f"Thuật toán: {result.algorithm}\n"
            f"Best value: {result.best_value:.2f}\n"
            f"Best weight: {result.best_weight:.2f} / {self.instance.capacity:.2f}\n"
            f"Hợp lệ: {result.is_feasible}\n"
            f"Thời gian chạy: {result.runtime_sec:.4f} giây\n"
            f"Số kiện được chọn: {sum(result.best_solution)}\n"
            f"Danh sách ID: {', '.join(selected_ids[:30])}{'...' if len(selected_ids) > 30 else ''}\n"
        )

    def _draw_history(self, ax, result: OptimizationResult, title: str):
        ax.clear()
        ax.plot(range(1, len(result.history_best) + 1), result.history_best, label="Best")
        if result.history_avg:
            ax.plot(range(1, len(result.history_avg) + 1), result.history_avg, label="Average")
        ax.set_title(title)
        ax.set_xlabel("Iteration / Generation")
        ax.set_ylabel("Fitness (Total Value)")
        ax.grid(True, alpha=0.3)
        ax.legend()

    def _on_ga_done(self, result: OptimizationResult):
        self.last_result = result
        self.ga_summary.delete("1.0", "end")
        self.ga_summary.insert("1.0", self._format_result_text(result))
        self._draw_history(self.ga_ax, result, "GA Convergence")
        self.ga_canvas.draw()
        self.truck_canvas.set_solution(self.instance, result.best_solution)
        self.notebook.select(self.data_tab)
        self._set_status("GA hoàn tất.")

    def _on_cso_done(self, result: OptimizationResult):
        self.last_result = result
        self.cso_summary.delete("1.0", "end")
        self.cso_summary.insert("1.0", self._format_result_text(result))
        self._draw_history(self.cso_ax, result, "CSO Convergence")
        self.cso_canvas.draw()
        self.truck_canvas.set_solution(self.instance, result.best_solution)
        self.notebook.select(self.data_tab)
        self._set_status("CSO hoàn tất.")

    def _on_benchmark_done(self, report: dict):
        self.compare_summary.delete("1.0", "end")

        lines = [
            f"Scenario: {report['scenario_key']}",
            f"Dataset: {report['instance_name']} ({report['difficulty']})",
            f"Số kiện hàng: {report['items']}",
            f"Tải trọng: {report['capacity']:.2f}",
            f"Thuật toán: {report['algorithm']}",
            f"Số lần chạy (runs): {report.get('n_runs', '')}",
            "",
            "Kết quả theo case (so sánh nội bộ):",
        ]

        for case in report["cases"]:
            lines.append(
                f"- {case['case_name']}: "
                f"value_mean={case['value']['mean']:.2f} (std={case['value']['std']:.2f}), "
                f"runtime_mean={case['runtime']['mean']:.4f}s"
            )

        self.compare_summary.insert("1.0", "\n".join(lines))

        self.compare_ax.clear()
        case_names = [c["case_name"] for c in report["cases"]]
        value_means = [c["value"]["mean"] for c in report["cases"]]

        self.compare_ax.bar(case_names, value_means, label="Mean best value")
        self.compare_ax.set_title(f"Internal study: {report['algorithm']} / {report['scenario_key']}")
        self.compare_ax.set_xlabel("Cases")
        self.compare_ax.set_ylabel("Mean best value")
        self.compare_ax.tick_params(axis="x", rotation=30)
        self.compare_ax.legend()
        self.compare_ax.grid(True, axis="y", alpha=0.3)
        self.compare_canvas.draw()

        self._set_status("Benchmark hoàn tất.")


def launch():
    app = App()
    app.mainloop()