"""
app.py  –  Knapsack Optimizer GUI
Layout:
  LEFT  (280px)  : menu điều khiển + dataset + algo config
  RIGHT (expand) : TOP (3/4) = xe tải sắp xếp kiện hàng
                   BOT (1/4) = biểu đồ hội tụ / benchmark
  Panels trượt xuống (slide-down) thay thế Toplevel
"""
from __future__ import annotations

import queue
import threading
import traceback
import tkinter as tk
from tkinter import ttk, messagebox

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from algorithms.cso.cso_solver import solve as solve_cso
from algorithms.ga.ga_solver import solve as solve_ga
from core.datasets import (generate_easy_problem,
                           generate_hard_problem,
                           generate_problem_random)
from core.models import KnapsackInstance, OptimizationResult
from experiments.benchmark import run_benchmark_in_memory
from experiments.scenarios import (DEFAULT_CSO_CONFIG, DEFAULT_GA_CONFIG,
                                   get_scenarios)
from gui.widgets.truck_canvas import TruckCanvas

# ─────────────────────────  THEME  ──────────────────────────────────────────
BG       = "#f4f6fb"
SURFACE  = "#ffffff"
SURF2    = "#f0f3fa"
BORDER   = "#dde3f2"
ACCENT   = "#4f7dff"
ACCH     = "#3360e0"
ACCENT2  = "#ff6b4a"
SUCCESS  = "#2ecb7e"
WARN     = "#f5a623"
TEXT     = "#1c2040"
DIM      = "#8890b0"

FN       = ("Segoe UI", 9)
FNB      = ("Segoe UI", 9,  "bold")
FNS      = ("Segoe UI", 8)
FNM      = ("Consolas", 8)
FNH      = ("Segoe UI", 11, "bold")


# ─────────────────────────  HELPERS  ────────────────────────────────────────
def _fr(parent, bg=SURFACE, **kw):
    return tk.Frame(parent, bg=bg, **kw)

def _lbl(parent, text, font=FN, fg=TEXT, bg=SURFACE, **kw):
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, **kw)

def _sep(parent, bg=BORDER):
    return tk.Frame(parent, bg=bg, height=1)

def _entry(parent, var, width=12):
    e = tk.Entry(parent, textvariable=var, font=FN, width=width,
                 bg=SURF2, fg=TEXT, relief="flat",
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT, insertbackground=ACCENT)
    return e

def _btn(parent, text, cmd, bg=ACCENT, fg="#fff", **kw):
    b = tk.Button(parent, text=text, command=cmd, font=FNB,
                  bg=bg, fg=fg, relief="flat", cursor="hand2",
                  activebackground=ACCH, activeforeground="#fff",
                  padx=10, pady=5, bd=0, **kw)
    b.bind("<Enter>", lambda e, c=bg: b.config(bg=ACCH))
    b.bind("<Leave>", lambda e, c=bg: b.config(bg=c))
    return b

def _section(parent, text):
    """Tiêu đề section nhỏ trong menu trái."""
    f = _fr(parent)
    f.pack(fill="x", padx=12, pady=(10, 2))
    _lbl(f, text, font=FNS, fg=DIM).pack(anchor="w")
    _sep(f).pack(fill="x", pady=(3, 0))
    return f


# ─────────────────────  SLIDE-DOWN PANEL  ───────────────────────────────────
class SlidePanel(tk.Frame):
    """
    Frame trượt xuống ngay trong cùng container.
    Dùng place() để overlay lên content bên dưới.
    """
    def __init__(self, anchor_widget: tk.Widget, width: int, max_height: int,
                 bg=SURFACE):
        self._anchor  = anchor_widget
        self._root    = anchor_widget.winfo_toplevel()
        self._width   = width
        self._maxh    = max_height
        self._visible = False
        self._anim_id = None

        super().__init__(self._root, bg=bg,
                         highlightbackground=BORDER, highlightthickness=1)
        self._cur_h = 0

    # ── public ──────────────────────────────────────────────────────────────
    def toggle(self):
        if self._visible:
            self._close()
        else:
            self._open()

    def close(self):
        if self._visible:
            self._close()

    # ── geometry ─────────────────────────────────────────────────────────────
    def _anchor_pos(self):
        a = self._anchor
        a.update_idletasks()
        x  = a.winfo_rootx() - self._root.winfo_rootx()
        y  = a.winfo_rooty() - self._root.winfo_rooty() + a.winfo_height() + 2
        sw = self._root.winfo_width()
        if x + self._width > sw:
            x = sw - self._width - 4
        return x, y

    # ── animation ────────────────────────────────────────────────────────────
    def _open(self):
        self._visible = True
        x, y = self._anchor_pos()
        self._cur_h = 0
        self.place(x=x, y=y, width=self._width, height=0)
        self.lift()
        self._animate_to(self._maxh)

    def _close(self):
        self._visible = False
        self._animate_to(0, done=lambda: self.place_forget())

    def _animate_to(self, target, done=None):
        if self._anim_id:
            try: self.after_cancel(self._anim_id)
            except: pass
        step = 28

        def tick():
            if not self.winfo_exists():
                return
            cur = self._cur_h
            diff = target - cur
            if abs(diff) <= step:
                self._cur_h = target
                x, y = self._anchor_pos()
                if target > 0:
                    self.place(x=x, y=y, width=self._width, height=target)
                if done:
                    done()
            else:
                self._cur_h = cur + (step if diff > 0 else -step)
                x, y = self._anchor_pos()
                self.place(x=x, y=y, width=self._width, height=self._cur_h)
                self._anim_id = self.after(16, tick)
        tick()

    def reposition(self):
        if self._visible:
            x, y = self._anchor_pos()
            self.place(x=x, y=y, width=self._width, height=self._cur_h)


# ═══════════════════════════════  APP  ═══════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Knapsack Optimizer  ·  GA & CSO")
        self.geometry("1380x840")
        self.minsize(1100, 680)
        self.configure(bg=BG)

        self.instance: KnapsackInstance = generate_easy_problem(30, seed=42)
        self.last_result: OptimizationResult | None = None
        self._task_q: queue.Queue = queue.Queue()

        self._mode  = "single"    # "single" | "benchmark"
        self._algo  = tk.StringVar(value="GA")

        # slide panels – created lazily
        self._sp_items:       SlidePanel | None = None
        self._sp_config:      SlidePanel | None = None
        self._sp_bench_info:  SlidePanel | None = None

        # config vars – created once
        self._init_vars()

        self._build_ui()
        self.after(120, self._poll)
        self.bind_all("<Button-1>", self._global_click, add="+")

    # ══════════════════════════  VARS  ═══════════════════════════════════════
    def _init_vars(self):
        self._n_items  = tk.IntVar(value=30)
        self._seed     = tk.IntVar(value=42)
        self._diff     = tk.StringVar(value="Easy")

        self.ga_vars = {
            k: (tk.IntVar(value=v) if isinstance(v, int)
                else tk.DoubleVar(value=v) if isinstance(v, float)
                else tk.BooleanVar(value=v) if isinstance(v, bool)
                else tk.StringVar(value=v))
            for k, v in {**DEFAULT_GA_CONFIG, "seed": 42}.items()
        }
        self.cso_vars = {
            k: (tk.IntVar(value=v) if isinstance(v, int)
                else tk.DoubleVar(value=v) if isinstance(v, float)
                else tk.BooleanVar(value=v) if isinstance(v, bool)
                else tk.StringVar(value=v))
            for k, v in {**DEFAULT_CSO_CONFIG, "seed": 42}.items()
        }

        self._bench_scenario = tk.StringVar(value=list(get_scenarios().keys())[0])
        self._bench_runs     = tk.IntVar(value=3)
        self._prog_var       = tk.IntVar(value=0)

    # ══════════════════════════  BUILD UI  ═══════════════════════════════════
    def _build_ui(self):
        # ── topbar ───────────────────────────────────────────────────────────
        top = _fr(self, bg=SURFACE, height=50)
        top.pack(fill="x"); top.pack_propagate(False)
        _sep(self).pack(fill="x")

        _lbl(top, "⬡  Knapsack Optimizer", font=("Segoe UI", 13, "bold"),
             fg=ACCENT, bg=SURFACE).pack(side="left", padx=18, pady=12)

        # mode tabs
        tf = _fr(top, bg=SURFACE); tf.pack(side="left", padx=10)
        self._tab_btns = {}
        for mode, label in [("single","Single Run"), ("benchmark","Benchmark")]:
            f2 = _fr(tf, bg=SURFACE); f2.pack(side="left")
            b  = tk.Button(f2, text=label, font=FN, bg=SURFACE, fg=DIM,
                           relief="flat", cursor="hand2", padx=14, pady=10, bd=0,
                           command=lambda m=mode: self._set_mode(m))
            b.pack()
            ind = _fr(f2, bg=SURFACE, height=2); ind.pack(fill="x")
            self._tab_btns[mode] = (b, ind)

        self._status_var = tk.StringVar(value="Sẵn sàng.")
        _lbl(top, "", textvariable=self._status_var, font=FNS,
             fg=DIM, bg=SURFACE).pack(side="right", padx=18)

        # ── body PanedWindow ─────────────────────────────────────────────────
        pw = tk.PanedWindow(self, orient="horizontal", bg=BG,
                            sashwidth=5, sashrelief="flat", handlesize=0)
        pw.pack(fill="both", expand=True, padx=8, pady=8)

        # Left panel
        self._left_frame = _fr(pw, bg=SURFACE,
                               highlightbackground=BORDER, highlightthickness=1)
        pw.add(self._left_frame, minsize=220, width=270)

        # Right panel (vertical paned)
        self._right_pw = tk.PanedWindow(pw, orient="vertical", bg=BG,
                                        sashwidth=5, sashrelief="flat", handlesize=0)
        pw.add(self._right_pw, minsize=500)

        # Right-top: xe tải
        self._truck_frame = _fr(self._right_pw, bg=SURFACE,
                                highlightbackground=BORDER, highlightthickness=1)
        self._right_pw.add(self._truck_frame, minsize=180)

        # Right-bottom: biểu đồ
        self._chart_frame = _fr(self._right_pw, bg=SURFACE,
                                highlightbackground=BORDER, highlightthickness=1)
        self._right_pw.add(self._chart_frame, minsize=100)

        self._build_left()
        self._build_truck_area()
        self._build_chart_area()
        self._set_mode("single")


    # ══════════════════════════  LEFT PANEL  ═════════════════════════════════
    def _build_left(self):
        p = self._left_frame
        cv = tk.Canvas(p, bg=SURFACE, highlightthickness=0)
        sb = ttk.Scrollbar(p, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)

        inner = _fr(cv, bg=SURFACE)
        cv.create_window((0, 0), window=inner, anchor="nw", tags="inner")

        def _resize(e):
            cv.configure(scrollregion=cv.bbox("all"))
            cv.itemconfig("inner", width=cv.winfo_width())
        inner.bind("<Configure>", _resize)
        cv.bind("<Configure>", lambda e: cv.itemconfig("inner", width=e.width))

        self._left_inner = inner
        self._build_dataset_section(inner)
        self._left_mode_frame = _fr(inner, bg=SURFACE)
        self._left_mode_frame.pack(fill="x")

    def _build_dataset_section(self, parent):
        _section(parent, "DATASET")
        f = _fr(parent); f.pack(fill="x", padx=12, pady=4)

        # row: n_items + seed
        r1 = _fr(f); r1.pack(fill="x", pady=(0, 4))
        fl = _fr(r1); fl.pack(side="left", fill="x", expand=True, padx=(0, 6))
        _lbl(fl, "Số kiện hàng", font=FNS, fg=DIM).pack(anchor="w")
        _entry(fl, self._n_items, width=7).pack(fill="x", ipady=3)

        fr2 = _fr(r1); fr2.pack(side="left")
        _lbl(fr2, "Seed", font=FNS, fg=DIM).pack(anchor="w")
        _entry(fr2, self._seed, width=6).pack(ipady=3)

        # row: combo + sinh
        r2 = _fr(f); r2.pack(fill="x", pady=(0, 4))
        cb = ttk.Combobox(r2, textvariable=self._diff,
                          values=["Easy","Hard","Random"],
                          state="readonly", font=FN, width=9)
        cb.pack(side="left", fill="x", expand=True, ipady=3)
        _btn(r2, "Sinh", self._generate_instance, bg=SUCCESS).pack(side="left", padx=(6,0))

        # nút chi tiết kiện hàng
        self._items_btn = tk.Button(
            f, text="📦  Chi tiết kiện hàng  ▾",
            font=FNS, bg=SURF2, fg=TEXT, relief="flat", cursor="hand2",
            padx=8, pady=5, anchor="w",
            command=self._toggle_items,
        )
        self._items_btn.pack(fill="x", pady=(2, 0))

        self._info_var = tk.StringVar(value="30 kiện · cap: —")
        _lbl(f, "", textvariable=self._info_var, font=FNS, fg=DIM).pack(anchor="w", pady=(2,0))

    def _refresh_left_mode(self):
        # Reset widget refs trước khi destroy
        self._result_text       = None
        self._bench_result_text = None
        for w in self._left_mode_frame.winfo_children():
            w.destroy()
        # Đóng slide panels đang mở nếu có
        for sp_attr in ("_sp_config", "_sp_items", "_sp_bench_info"):
            sp = getattr(self, sp_attr, None)
            if sp and sp._visible:
                sp.close()
            setattr(self, sp_attr, None)
        if self._mode == "single":
            self._build_single_section(self._left_mode_frame)
        else:
            self._build_bench_section(self._left_mode_frame)

    def _build_single_section(self, parent):
        _section(parent, "THUẬT TOÁN")
        af = _fr(parent); af.pack(fill="x", padx=12, pady=4)

        rb_f = _fr(af); rb_f.pack(fill="x", pady=(0,4))
        style = ttk.Style()
        style.configure("Algo.TRadiobutton", background=SURFACE, font=FNB)
        for algo in ("GA","CSO"):
            rb = tk.Radiobutton(rb_f, text=algo, variable=self._algo, value=algo,
                                font=FNB, bg=SURFACE, fg=TEXT, selectcolor=SURFACE,
                                activebackground=SURFACE, indicatoron=0, relief="flat",
                                padx=18, pady=6, cursor="hand2",
                                command=self._on_algo_change)
            rb.pack(side="left", padx=(0,6))

        # nút thiết lập
        self._cfg_btn = tk.Button(
            af, text="⚙  Thiết lập cấu hình  ▾",
            font=FNS, bg=SURF2, fg=TEXT, relief="flat", cursor="hand2",
            padx=8, pady=5, anchor="w",
            command=self._toggle_config,
        )
        self._cfg_btn.pack(fill="x", pady=(0,6))

        _sep(af).pack(fill="x", pady=4)
        _btn(af, "▶  Chạy", self._run_single, bg=ACCENT).pack(fill="x", pady=4)

        _sep(af).pack(fill="x", pady=(8,4))

        # Kết quả chi tiết — inline, luôn hiển thị (không dùng slide)
        _lbl(af, "📊  Kết quả chi tiết", font=FNS, fg=DIM).pack(anchor="w", pady=(0,2))
        self._result_text = tk.Text(
            af, font=FNM, bg=SURF2, fg=TEXT, relief="flat",
            wrap="word", height=9,
            highlightthickness=1, highlightbackground=BORDER,
            state="disabled",
        )
        self._result_text.pack(fill="x", pady=(0,4))

    def _build_bench_section(self, parent):
        _section(parent, "BENCHMARK")
        bf = _fr(parent); bf.pack(fill="x", padx=12, pady=4)

        _lbl(bf, "Scenario", font=FNS, fg=DIM).pack(anchor="w")
        sr = _fr(bf); sr.pack(fill="x", pady=(2,6))
        ttk.Combobox(sr, textvariable=self._bench_scenario,
                     values=list(get_scenarios().keys()),
                     state="readonly", font=FNS, width=17
                     ).pack(side="left", fill="x", expand=True, ipady=3)
        self._bench_info_btn = tk.Button(
            sr, text="ℹ", font=FNB, bg=SURF2, fg=ACCENT,
            relief="flat", cursor="hand2", padx=8,
            command=self._toggle_bench_info,
        )
        self._bench_info_btn.pack(side="left", padx=(4,0))

        r = _fr(bf); r.pack(fill="x", pady=(0,4))
        _lbl(r, "Số lần chạy", font=FNS, fg=DIM, width=12, anchor="w").pack(side="left")
        _entry(r, self._bench_runs, width=6).pack(side="left", ipady=3)

        _lbl(bf, "Tiến độ", font=FNS, fg=DIM).pack(anchor="w", pady=(4,0))
        ttk.Progressbar(bf, variable=self._prog_var, maximum=100).pack(fill="x", pady=(2,0))
        self._prog_lbl = _lbl(bf, "", font=FNS, fg=DIM)
        self._prog_lbl.pack(anchor="w")

        _btn(bf, "▦  Chạy Benchmark", self._run_benchmark, bg=WARN).pack(fill="x", pady=(10,4))

        _sep(bf).pack(fill="x", pady=(8,4))
        _lbl(bf, "📋  Kết quả benchmark", font=FNS, fg=DIM).pack(anchor="w", pady=(0,2))
        self._bench_result_text = tk.Text(
            bf, font=FNM, bg=SURF2, fg=TEXT, relief="flat",
            wrap="word", height=14,
            highlightthickness=1, highlightbackground=BORDER,
            state="disabled",
        )
        sb_br = ttk.Scrollbar(bf, command=self._bench_result_text.yview)
        self._bench_result_text.configure(yscrollcommand=sb_br.set)
        self._bench_result_text.pack(side="left", fill="both", expand=True)
        sb_br.pack(side="right", fill="y")

    # ══════════════════════════  TRUCK AREA  ═════════════════════════════════
    def _build_truck_area(self):
        p = self._truck_frame
        hdr = _fr(p); hdr.pack(fill="x", padx=14, pady=(10,4))
        _lbl(hdr, "Sắp xếp kiện hàng trên xe tải", font=FNB, fg=TEXT).pack(side="left")
        self._truck_algo_lbl = _lbl(hdr, "", font=FNS, fg=DIM)
        self._truck_algo_lbl.pack(side="right")

        _sep(p).pack(fill="x", padx=10)

        self._truck = TruckCanvas(p)
        self._truck.pack(fill="both", expand=True, padx=8, pady=8)
        self._truck.set_solution(self.instance, None)

    # ══════════════════════════  CHART AREA  ═════════════════════════════════
    def _build_chart_area(self):
        p = self._chart_frame

        hdr = _fr(p); hdr.pack(fill="x", padx=14, pady=(6,2))
        _lbl(hdr, "Biểu đồ", font=FNB, fg=TEXT).pack(side="left")
        tk.Button(hdr, text="⤢ phóng to", font=FNS, bg=SURFACE, fg=ACCENT,
                  relief="flat", cursor="hand2", padx=4,
                  command=self._zoom_chart).pack(side="right")
        _sep(p).pack(fill="x", padx=10)

        # Container — bind resize vào đây
        self._chart_container = _fr(p, bg=SURFACE)
        self._chart_container.pack(fill="both", expand=True, padx=6, pady=(2,6))

        # Figure 1: single run (hội tụ)
        self._fig_single = Figure(facecolor=SURFACE)
        self._fig_single.subplots_adjust(left=0.11, right=0.97, top=0.88, bottom=0.18)
        self._ax_single  = self._fig_single.add_subplot(111)
        self._style_ax(self._ax_single)
        self._ax_single.set_title("Chờ kết quả...", fontsize=9, color=DIM)
        self._canvas_single = FigureCanvasTkAgg(self._fig_single,
                                                master=self._chart_container)

        # Figure 2: benchmark (bar chart)
        self._fig_bench = Figure(facecolor=SURFACE)
        self._fig_bench.subplots_adjust(left=0.10, right=0.97, top=0.88, bottom=0.28)
        self._ax_bench  = self._fig_bench.add_subplot(111)
        self._style_ax(self._ax_bench)
        self._ax_bench.set_title("Chờ kết quả benchmark...", fontsize=9, color=DIM)
        self._canvas_bench = FigureCanvasTkAgg(self._fig_bench,
                                               master=self._chart_container)

        # Bind resize → figure luôn vừa ô
        self._chart_container.bind("<Configure>", self._on_chart_resize)

        # Active pointers (dùng cho zoom)
        self._ax     = self._ax_single
        self._canvas = self._canvas_single
        self._active_fig = self._fig_single

        self._show_chart_for_mode("single")

    def _show_chart_for_mode(self, mode: str):
        """Hiện canvas đúng với mode, ẩn canvas còn lại."""
        if mode == "single":
            self._canvas_bench.get_tk_widget().pack_forget()
            self._canvas_single.get_tk_widget().pack(fill="both", expand=True)
            self._ax         = self._ax_single
            self._canvas     = self._canvas_single
            self._active_fig = self._fig_single
        else:
            self._canvas_single.get_tk_widget().pack_forget()
            self._canvas_bench.get_tk_widget().pack(fill="both", expand=True)
            self._ax         = self._ax_bench
            self._canvas     = self._canvas_bench
            self._active_fig = self._fig_bench
        self._canvas.draw_idle()

    def _on_chart_resize(self, event):
        w = event.width; h = event.height
        if w < 20 or h < 20:
            return
        dpi = self._fig_single.get_dpi()
        fw = w / dpi; fh = h / dpi
        for fig in (self._fig_single, self._fig_bench):
            try:
                fig.set_size_inches(fw, fh, forward=True)
            except Exception:
                pass
        try:
            self._canvas.draw_idle()
        except Exception:
            pass

    def _style_ax(self, ax):
        ax.set_facecolor(SURF2)
        ax.tick_params(labelsize=8, colors=DIM)
        for sp in ax.spines.values(): sp.set_edgecolor(BORDER)
        ax.grid(True, color=BORDER, linewidth=0.6)


    # ══════════════════════════  SLIDE PANELS  ═══════════════════════════════

    # ── Chi tiết kiện hàng ───────────────────────────────────────────────────
    def _toggle_items(self):
        if self._sp_items is None:
            self._sp_items = SlidePanel(self._items_btn, width=420, max_height=300)
            self._build_items_content(self._sp_items)
        self._sp_items.toggle()
        self._items_btn.config(
            text="📦  Chi tiết kiện hàng  ▴" if (self._sp_items and self._sp_items._visible)
            else "📦  Chi tiết kiện hàng  ▾"
        )

    def _build_items_content(self, panel):
        hdr = _fr(panel); hdr.pack(fill="x", padx=10, pady=(8,4))
        _lbl(hdr, "Chi tiết kiện hàng", font=FNB, fg=TEXT).pack(side="left")
        tk.Button(hdr, text="✕", font=FNS, bg=SURFACE, fg=DIM,
                  relief="flat", cursor="hand2",
                  command=lambda: (self._sp_items.close(),
                                   self._items_btn.config(text="📦  Chi tiết kiện hàng  ▾"))
                  ).pack(side="right")

        tf = _fr(panel); tf.pack(fill="both", expand=True, padx=10, pady=(0,10))
        cols = ("ID","Khối lượng","Giá trị","Ưu tiên","v/w")
        self._item_tree = ttk.Treeview(tf, columns=cols, show="headings", height=9)
        for c, w in zip(cols, [45,90,80,70,70]):
            self._item_tree.heading(c, text=c)
            self._item_tree.column(c, width=w, anchor="center")
        sb2 = ttk.Scrollbar(tf, orient="vertical", command=self._item_tree.yview)
        self._item_tree.configure(yscrollcommand=sb2.set)
        self._item_tree.pack(side="left", fill="both", expand=True)
        sb2.pack(side="right", fill="y")
        self._reload_tree()

    def _reload_tree(self):
        if not hasattr(self, "_item_tree") or self._item_tree is None:
            return
        self._item_tree.delete(*self._item_tree.get_children())
        for it in self.instance.items:
            self._item_tree.insert("","end",
                values=(it.id, it.weight, it.value, it.priority,
                        round(it.value/max(it.weight,1e-9), 2)))

    # ── Cấu hình thuật toán ──────────────────────────────────────────────────
    def _toggle_config(self):
        if self._sp_config is None:
            self._sp_config = SlidePanel(self._cfg_btn, width=380, max_height=400)
            self._build_config_content(self._sp_config)
        self._sp_config.toggle()
        self._cfg_btn.config(
            text="⚙  Thiết lập cấu hình  ▴" if (self._sp_config and self._sp_config._visible)
            else "⚙  Thiết lập cấu hình  ▾"
        )

    def _build_config_content(self, panel):
        hdr = _fr(panel); hdr.pack(fill="x", padx=10, pady=(8,4))
        _lbl(hdr, "Thiết lập cấu hình", font=FNB, fg=TEXT).pack(side="left")

        nb = ttk.Notebook(panel)
        nb.pack(fill="both", expand=True, padx=8, pady=4)

        ga_f  = _fr(nb); nb.add(ga_f,  text="  GA  ")
        cso_f = _fr(nb); nb.add(cso_f, text="  CSO  ")

        def add_row(parent, label, var, wtype="entry", values=None):
            r = _fr(parent); r.pack(fill="x", padx=8, pady=2)
            _lbl(r, label, font=FNS, fg=DIM, width=22, anchor="w").pack(side="left")
            if wtype == "combo":
                w = ttk.Combobox(r, textvariable=var, values=values or [],
                                 state="readonly", font=FNS, width=13)
            elif wtype == "check":
                w = tk.Checkbutton(r, variable=var, bg=SURFACE,
                                   activebackground=SURFACE, font=FNS)
            else:
                w = _entry(r, var, width=13)
            w.pack(side="left")

        for k, l in [
            ("population_size","Pop. size"), ("generations","Generations"),
            ("crossover_rate","Crossover rate"), ("mutation_rate","Mutation rate ≤0.05"),
            ("elitism_count","Elitism count"), ("delta_generations","Delta gen."),
            ("seed","Seed"),
        ]:
            add_row(ga_f, l, self.ga_vars[k])
        add_row(ga_f,"Selection",self.ga_vars["selection"],"combo",["roulette","tournament","rank"])
        add_row(ga_f,"Crossover",self.ga_vars["crossover"],"combo",["one_point","two_point","uniform"])
        add_row(ga_f,"Mutation", self.ga_vars["mutation"], "combo",["bit_flip","swap","inversion"])
        add_row(ga_f,"Delta stop",self.ga_vars["use_delta_stop"],"check")

        for k, l in [
            ("num_cats","Num cats"), ("max_iter","Max iterations"),
            ("mr","Mixture ratio MR"), ("smp","Seeking pool SMP"),
            ("srd","Seeking range SRD"), ("cdc","Dim. count CDC"),
            ("c1","Acceleration c1"), ("vmin","Vmin"), ("vmax","Vmax"), ("seed","Seed"),
        ]:
            add_row(cso_f, l, self.cso_vars[k])

        bf = _fr(panel); bf.pack(fill="x", padx=8, pady=(4,10))
        _btn(bf, "💾  Lưu & Đóng", self._save_config, bg=SUCCESS).pack(fill="x")

    def _save_config(self):
        if self._sp_config:
            self._sp_config.close()
        self._cfg_btn.config(text="⚙  Thiết lập cấu hình  ▾")
        self._set_status("Đã lưu cấu hình.")

    # ── Kết quả chi tiết — được tạo inline trong _build_single_section ─────

    # ── Benchmark info ────────────────────────────────────────────────────────
    def _toggle_bench_info(self):
        if self._sp_bench_info is None:
            self._sp_bench_info = SlidePanel(self._bench_info_btn, width=400, max_height=320)
            self._build_bench_info_content(self._sp_bench_info)
        else:
            self._refresh_bench_info()
        self._sp_bench_info.toggle()

    def _build_bench_info_content(self, panel):
        hdr = _fr(panel); hdr.pack(fill="x", padx=10, pady=(8,4))
        _lbl(hdr, "Chi tiết scenario", font=FNB, fg=TEXT).pack(side="left")
        tk.Button(hdr, text="✕", font=FNS, bg=SURFACE, fg=DIM,
                  relief="flat", cursor="hand2",
                  command=self._sp_bench_info.close).pack(side="right")
        self._bench_info_text = tk.Text(panel, font=FNM, bg=SURF2, fg=TEXT,
                                        relief="flat", wrap="word", height=12,
                                        highlightthickness=1, highlightbackground=BORDER)
        sb2 = ttk.Scrollbar(panel, command=self._bench_info_text.yview)
        self._bench_info_text.configure(yscrollcommand=sb2.set)
        self._bench_info_text.pack(side="left", fill="both", expand=True, padx=(10,0), pady=(0,10))
        sb2.pack(side="right", fill="y", pady=(0,10), padx=(0,4))
        self._refresh_bench_info()

    def _refresh_bench_info(self):
        if not hasattr(self, "_bench_info_text"):
            return
        key   = self._bench_scenario.get()
        cases = get_scenarios().get(key, [])
        lines = [f"Scenario: {key}\n{len(cases)} case(s)\n\n"]
        for name, cfg in cases:
            lines.append(f"▸ {name}\n")
            for k, v in cfg.items():
                lines.append(f"   {k}: {v}\n")
            lines.append("\n")
        self._bench_info_text.configure(state="normal")
        self._bench_info_text.delete("1.0","end")
        self._bench_info_text.insert("1.0","".join(lines))
        self._bench_info_text.configure(state="disabled")

    # ── Zoom biểu đồ ─────────────────────────────────────────────────────────
    def _zoom_chart(self):
        win = tk.Toplevel(self)
        win.title("Biểu đồ – Phóng to")
        win.geometry("820x520")
        win.configure(bg=SURFACE)

        fig2 = Figure(facecolor=SURFACE)
        ax2  = fig2.add_subplot(111)
        self._style_ax(ax2)
        for line in self._ax.get_lines():
            ax2.plot(line.get_xdata(), line.get_ydata(),
                     color=line.get_color(), linewidth=line.get_linewidth()+0.5,
                     linestyle=line.get_linestyle(), label=line.get_label(),
                     alpha=line.get_alpha() or 1.0)
        for patch in self._ax.patches:
            from matplotlib.patches import Rectangle
            ax2.bar([patch.get_x() + patch.get_width()/2],
                    [patch.get_height()], width=patch.get_width()*0.9,
                    color=patch.get_facecolor(), alpha=0.85)
        ax2.set_title(self._ax.get_title(), fontsize=11, color=TEXT)
        ax2.set_xlabel(self._ax.get_xlabel(), fontsize=9, color=DIM)
        ax2.set_ylabel(self._ax.get_ylabel(), fontsize=9, color=DIM)
        handles = [l for l in self._ax.get_lines() if l.get_label() and not l.get_label().startswith("_")]
        if handles:
            ax2.legend(fontsize=9)
        fig2.tight_layout()

        c2 = FigureCanvasTkAgg(fig2, master=win)
        c2.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        c2.draw()

    # ══════════════════════════  MODE SWITCH  ════════════════════════════════
    def _set_mode(self, mode):
        self._mode = mode
        for m, (b, ind) in self._tab_btns.items():
            active = (m == mode)
            b.config(fg=ACCENT if active else DIM,
                     font=FNB if active else FN)
            ind.config(bg=ACCENT if active else SURFACE)
        self._refresh_left_mode()
        self._apply_mode_layout(mode)

    def _apply_mode_layout(self, mode):
        self.update_idletasks()
        total = self._right_pw.winfo_height()
        if total < 10:
            # Chưa render xong, thử lại sau
            self.after(100, lambda: self._apply_mode_layout(mode))
            return

        if mode == "single":
            # Hiện truck frame nếu đang bị ẩn
            panes = self._right_pw.panes()
            if str(self._truck_frame) not in [str(p) for p in panes]:
                self._right_pw.add(self._truck_frame, minsize=180, before=self._chart_frame)
            # Tỉ lệ 3:1 — truck chiếm 75%
            self._right_pw.sash_place(0, 0, int(total * 0.75))
        else:
            # Benchmark: ẩn truck frame, chỉ còn biểu đồ
            panes = self._right_pw.panes()
            if str(self._truck_frame) in [str(p) for p in panes]:
                self._right_pw.remove(self._truck_frame)

        # Chuyển canvas biểu đồ đúng với mode
        self._show_chart_for_mode(mode)

    def _on_algo_change(self):
        pass  # extensible

    # ══════════════════════════  DATASET  ════════════════════════════════════
    def _generate_instance(self):
        n    = self._n_items.get()
        seed = self._seed.get()
        diff = self._diff.get().lower()
        if diff == "easy":   self.instance = generate_easy_problem(n, seed=seed)
        elif diff == "hard": self.instance = generate_hard_problem(n, seed=seed)
        else:                self.instance = generate_problem_random(n, seed=seed)

        cap = self.instance.capacity
        self._info_var.set(f"{len(self.instance.items)} kiện · cap: {cap:.1f}")
        self._reload_tree()
        self._truck.set_solution(self.instance, None)
        self._set_status(f"Dataset: {self.instance.name}")

    # ══════════════════════════  RUN  ════════════════════════════════════════
    def _run_background(self, worker, callback, msg="Đang chạy..."):
        self._set_status(msg)
        def task():
            try:
                self._task_q.put(("ok", callback, worker()))
            except Exception:
                self._task_q.put(("err", None, traceback.format_exc()))
        threading.Thread(target=task, daemon=True).start()

    def _run_single(self):
        algo = self._algo.get()
        if algo == "GA":
            mr = self.ga_vars["mutation_rate"].get()
            if mr > 0.05:
                messagebox.showwarning("Cảnh báo", f"mutation_rate={mr:.3f} vượt 0.05!")
                return
            config = {k: v.get() for k, v in self.ga_vars.items() if k != "seed"}
            seed   = self.ga_vars["seed"].get()
            self._run_background(
                lambda: solve_ga(self.instance, config, seed=seed),
                self._on_single_done, "GA đang tối ưu..."
            )
        else:
            config = {k: v.get() for k, v in self.cso_vars.items() if k != "seed"}
            seed   = self.cso_vars["seed"].get()
            self._run_background(
                lambda: solve_cso(self.instance, config, seed=seed),
                self._on_single_done, "CSO đang tối ưu..."
            )

    def _run_benchmark(self):
        key    = self._bench_scenario.get()
        n_runs = self._bench_runs.get()
        self._prog_var.set(0)
        self._prog_lbl.config(text="Chuẩn bị...")

        def prog_cb(cur, total, name):
            self._task_q.put(("prog", None, (int(cur/total*100), f"{name} ({cur}/{total})")))

        self._run_background(
            lambda: run_benchmark_in_memory(
                self.instance, scenario_key=key,
                n_runs=n_runs, progress_callback=prog_cb,
            ),
            self._on_bench_done, f"Benchmark '{key}'..."
        )

    # ══════════════════════════  CALLBACKS  ══════════════════════════════════
    def _poll(self):
        try:
            while True:
                kind, cb, payload = self._task_q.get_nowait()
                if kind == "ok":
                    cb(payload)
                elif kind == "prog":
                    pct, lbl = payload
                    self._prog_var.set(pct)
                    self._prog_lbl.config(text=lbl)
                else:
                    self._set_status("Lỗi.")
                    messagebox.showerror("Lỗi", payload)
        except queue.Empty:
            pass
        self.after(120, self._poll)

    def _on_single_done(self, result: OptimizationResult):
        self.last_result = result
        self._truck.set_solution(self.instance, result.best_solution)
        self._truck_algo_lbl.config(
            text=f"{result.algorithm}  ·  value={result.best_value:.1f}"
                 f"  ·  weight={result.best_weight:.1f}/{self.instance.capacity:.1f}"
        )
        self._draw_convergence(result)
        self._update_result_text(result)
        self._set_status(
            f"{result.algorithm} ✓  value={result.best_value:.2f}  "
            f"t={result.runtime_sec:.3f}s"
        )

    def _on_bench_done(self, report: dict):
        self._prog_var.set(100)
        self._prog_lbl.config(text="Hoàn tất!")
        self._draw_benchmark(report)
        self._update_bench_result_text(report)
        self._set_status(f"Benchmark ✓  {report['scenario_key']}")

    def _update_bench_result_text(self, report: dict):
        if not hasattr(self, "_bench_result_text") or self._bench_result_text is None:
            return
        lines = [
            f"Scenario  : {report['scenario_key']}\n",
            f"Dataset   : {report['instance_name']} ({report['difficulty']})\n",
            f"Items     : {report['items']}   Cap: {report['capacity']:.1f}\n",
            f"Algorithm : {report['algorithm']}   Runs: {report['n_runs']}\n",
            "\n",
            f"{'Case':<18} {'Mean':>8} {'Std':>7} {'Time(s)':>8}\n",
            "─" * 44 + "\n",
        ]
        best_case = max(report["cases"], key=lambda c: c["value"]["mean"])
        for c in report["cases"]:
            marker = " ★" if c["case_name"] == best_case["case_name"] else ""
            lines.append(
                f"{c['case_name']:<18} {c['value']['mean']:>8.1f}"
                f" {c['value']['std']:>7.2f} {c['runtime']['mean']:>8.4f}{marker}\n"
            )
        self._bench_result_text.configure(state="normal")
        self._bench_result_text.delete("1.0", "end")
        self._bench_result_text.insert("1.0", "".join(lines))
        # Highlight dòng best
        content_lines = "".join(lines).split("\n")
        for i, line in enumerate(content_lines):
            if "★" in line:
                self._bench_result_text.tag_add("best", f"{i+1}.0", f"{i+1}.end")
        self._bench_result_text.tag_configure("best", foreground=SUCCESS, font=FNM)
        self._bench_result_text.configure(state="disabled")

    # ══════════════════════════  DRAW  ═══════════════════════════════════════
    def _draw_convergence(self, result: OptimizationResult):
        ax = self._ax_single
        ax.clear(); self._style_ax(ax)
        color = ACCENT if result.algorithm == "GA" else ACCENT2
        xs = range(1, len(result.history_best)+1)
        ax.plot(xs, result.history_best, color=color, lw=1.8, label="Best")
        if result.history_avg:
            ax.plot(xs, result.history_avg, color=DIM, lw=1,
                    ls="--", alpha=0.65, label="Average")
        ax.set_title(f"{result.algorithm} — Hội tụ", fontsize=10, color=TEXT, pad=6)
        ax.set_xlabel("Generation / Iteration", fontsize=8, color=DIM, labelpad=4)
        ax.set_ylabel("Fitness Value", fontsize=8, color=DIM, labelpad=4)
        ax.legend(fontsize=8, framealpha=0.9, loc="lower right")
        ax.margins(x=0.01)
        self._canvas_single.draw_idle()

    def _draw_benchmark(self, report: dict):
        import numpy as np
        ax = self._ax_bench
        ax.clear(); self._style_ax(ax)

        cases = report["cases"]
        names = [c["case_name"] for c in cases]
        means = [c["value"]["mean"] for c in cases]
        stds  = [c["value"]["std"]  for c in cases]
        rts   = [c["runtime"]["mean"] for c in cases]
        n = len(names)
        if n == 0:
            self._canvas_bench.draw_idle()
            return

        y = list(range(n))

        # Màu gradient: cột cao hơn → đậm hơn
        max_v = max(means) if max(means) > 0 else 1
        colors = []
        for v in means:
            t = v / max_v          # 0..1
            r = int(0x4f + t * (0x1a - 0x4f))  # ACCENT → darker
            g = int(0x7d + t * (0x3f - 0x7d))
            b = int(0xff + t * (0xcc - 0xff))
            colors.append(f"#{r:02x}{g:02x}{b:02x}")

        # Highlight cột tốt nhất
        best_i = int(np.argmax(means))
        colors[best_i] = SUCCESS

        # Vẽ horizontal bar
        ax.grid(True, axis="x", color=BORDER, linewidth=0.5, zorder=0)
        bars = ax.barh(y, means, xerr=stds, height=0.52,
                       color=colors, alpha=0.88,
                       error_kw={"elinewidth": 1.0, "ecolor": "#aab0cc",
                                 "capsize": 3},
                       zorder=3)

        # Nhãn giá trị + runtime bên phải mỗi cột
        pad = max_v * 0.012
        for i, (bar, v, rt) in enumerate(zip(bars, means, rts)):
            w = bar.get_width()
            star = " ★" if i == best_i else ""
            ax.text(w + pad, bar.get_y() + bar.get_height()/2,
                    f"{v:.1f}{star}",
                    va="center", ha="left",
                    fontsize=7.5,
                    color=SUCCESS if i == best_i else TEXT,
                    fontweight="bold" if i == best_i else "normal")

        # Trục Y: tên case — canh phải, font nhỏ vừa đọc
        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=max(6.5, 9.5 - n * 0.4),
                           color=TEXT)
        ax.tick_params(axis="y", length=0, pad=4)
        ax.invert_yaxis()   # case đầu tiên ở trên

        # Trục X
        ax.set_xlabel("Mean Best Value (±std)", fontsize=8,
                      color=DIM, labelpad=4)
        ax.tick_params(axis="x", labelsize=7.5, colors=DIM)

        # Đường dọc tại giá trị mean toàn bộ
        grand_mean = float(np.mean(means))
        ax.axvline(grand_mean, color=ACCENT2, linewidth=1,
                   linestyle="--", alpha=0.7,
                   label=f"avg={grand_mean:.1f}")

        # Mở rộng xlim để chữ bên phải không bị cắt
        ax.set_xlim(0, max_v * 1.22)

        ax.set_title(
            f"{report['algorithm']}  ·  {report['scenario_key']}",
            fontsize=8.5, color=TEXT, pad=5)
        ax.legend(fontsize=7, framealpha=0.8, loc="lower right")

        # Xoá viền trên/phải cho thoáng
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        self._canvas_bench.draw_idle()

    # ══════════════════════════  RESULT TEXT  ════════════════════════════════
    def _update_result_text(self, result: OptimizationResult):
        if not hasattr(self, "_result_text") or self._result_text is None:
            return
        sel = [str(self.instance.items[i].id)
               for i, g in enumerate(result.best_solution) if g == 1]
        text = (
            f"Thuật toán : {result.algorithm}\n"
            f"Best value : {result.best_value:.2f}\n"
            f"Weight     : {result.best_weight:.2f} / {self.instance.capacity:.2f}\n"
            f"Hợp lệ     : {'✓ Có' if result.is_feasible else '✗ Không'}\n"
            f"Runtime    : {result.runtime_sec:.4f}s\n"
            f"Kiện chọn  : {sum(result.best_solution)}/{len(result.best_solution)}\n"
            f"IDs        : {', '.join(sel[:25])}{'...' if len(sel)>25 else ''}\n"
        )
        self._result_text.configure(state="normal")
        self._result_text.delete("1.0","end")
        self._result_text.insert("1.0", text)
        self._result_text.configure(state="disabled")

    # ══════════════════════════  GLOBAL CLICK  ═══════════════════════════════
    def _global_click(self, event):
        """Đóng slide panel khi click ra ngoài."""
        panels_btns = [
            (self._sp_items,      getattr(self,"_items_btn",None)),
            (self._sp_bench_info, getattr(self,"_bench_info_btn",None)),
        ]
        for sp, trigger_btn in panels_btns:
            if sp is None or not sp._visible:
                continue
            w = event.widget
            inside = False
            while w:
                if w is sp or w is trigger_btn:
                    inside = True
                    break
                try: w = w.master
                except: break
            if not inside:
                sp.close()

    def _set_status(self, text):
        self._status_var.set(text)


def launch():
    app = App()
    app.mainloop()