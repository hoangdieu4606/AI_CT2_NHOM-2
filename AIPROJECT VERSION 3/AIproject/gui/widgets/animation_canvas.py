"""
animation_canvas.py  –  AnimationCanvas widget
================================================
Hiển thị animation tuỳ theo thuật toán:

  GA  → Evolution Network  (cột thế hệ → cá thể → chromosome bar)
         + Panel mã vạch best chromosome (dưới cùng)
         + Tự động zoom để nhìn thấy hết tất cả cá thể

  CSO → Cat Swarm Visualization  (scatter 2D)
         + Panel 3D Fitness Landscape (bên phải, dùng matplotlib)
         + Panel mã vạch best chromosome (dưới cùng)
         + Mèo nhỏ & cách xa hơn

Thay đổi toggle:
  - Bật animation: chỉ HIỆN lại kết quả đã render, KHÔNG gọi start() lại.
  - start() chỉ được gọi từ _on_single_done (khi nhấn Chạy).
"""
from __future__ import annotations
import tkinter as tk
import random
import math

# matplotlib cho 3D panel (CSO)
try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    import numpy as np
    from mpl_toolkits.mplot3d import Axes3D          # noqa: F401
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    _HAS_MPL = True
except ImportError:
    _HAS_MPL = False

# ── Palette ──────────────────────────────────────────────────────────────────
C_BG         = "#f4f6fb"
C_NODE_BG    = "#ffffff"
C_NODE_BEST  = "#eef4ff"
C_TEXT       = "#1c2040"
C_TEXT_DIM   = "#8890b0"
C_BAR_1      = "#2ecb7e"
C_BAR_1_BEST = "#4f7dff"
C_BAR_0      = "#e8ecf4"
C_BORDER     = "#dde3f2"
C_LINE       = "#d5dbec"
C_LINE_BEST  = "#4f7dff"

# CSO palette
C_SEEK_BODY  = "#ffb347"
C_TRACE_BODY = "#4f7dff"
C_TRACE_BEST = "#2ecb7e"
C_GRID       = "#e8ecf8"
C_GBEST_RING = "#2ecb7e"

# Best-bar panel
C_PANEL_BG   = "#f0f3fa"
C_PANEL_BDR  = "#c8d0e8"

# ─────────────────────────────────────────────────────────────────────────────
#  AnimationCanvas
# ─────────────────────────────────────────────────────────────────────────────
class AnimationCanvas(tk.Frame):
    """
    Frame chứa:
      ┌─────────────────────────────┬──────────────┐
      │  Canvas chính (GA/CSO anim) │  3D panel    │  ← CSO only
      ├─────────────────────────────┴──────────────┤
      │  Best-chromosome bar panel (cả GA & CSO)   │
      └────────────────────────────────────────────┘
    """

    # chiều cao panel mã vạch best chromosome
    BEST_BAR_H = 54

    def __init__(self, master, **kw):
        kw.setdefault("bg", C_BG)
        super().__init__(master, **kw)

        # ── layout frames ────────────────────────────────────────────────────
        self._top_frame = tk.Frame(self, bg=C_BG)
        self._top_frame.pack(fill="both", expand=True)

        self._best_bar_frame = tk.Frame(self._top_frame, bg=C_PANEL_BG,
                                        height=self.BEST_BAR_H,
                                        highlightbackground=C_PANEL_BDR,
                                        highlightthickness=1)
        # best bar sẽ được pack sau khi biết layout

        # ── canvas chính ─────────────────────────────────────────────────────
        self._canvas = tk.Canvas(self._top_frame, bg=C_BG,
                                 highlightthickness=0)
        self._canvas.pack(side="left", fill="both", expand=True)

        # ── 3D panel (CSO, matplotlib) ───────────────────────────────────────
        self._panel3d_frame: tk.Frame | None = None
        self._fig3d        = None
        self._ax3d         = None
        self._canvas3d     = None
        self._rot_angle    = 0 # góc xoay tự động
        self._rot_elev     = 28         
        self._rot_id       = None       # after-id cho xoay

        # ── best-bar canvas ──────────────────────────────────────────────────
        self._bb_canvas = tk.Canvas(self._best_bar_frame, bg=C_PANEL_BG,
                                    highlightthickness=0,
                                    height=self.BEST_BAR_H)

        # ── state ────────────────────────────────────────────────────────────
        self._populations   = []
        self._current_gen   = 0
        self._anim_id       = None
        self._running       = False
        self._speed_ms      = 100
        self._history       = []
        self._algorithm     = "GA"
        self._n_items       = 30
        self._pop_size      = 20
        self._best_solution_chrom: list[int] = []

        # CSO
        self._cso_frames: list[dict] = []

        # best-chrom history per frame (both algos)
        self._frame_best_chroms: list[list[int]] = []

        # pan / zoom (GA canvas)
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._pan_start = None
        self._scale = 1.0

        # canvas event bindings
        c = self._canvas
        c.bind("<Configure>",       self._on_resize)
        c.bind("<ButtonPress-3>",   self._on_pan_start)
        c.bind("<B3-Motion>",       self._on_pan_move)
        c.bind("<ButtonRelease-3>", self._on_pan_end)
        c.bind("<MouseWheel>",      self._on_scroll)
        c.bind("<Button-4>",        self._on_scroll)
        c.bind("<Button-5>",        self._on_scroll)

    # ══════════════════════════════  PUBLIC API  ══════════════════════════════

    def start(self, history_best, best_solution=None, algorithm="GA",
              speed_ms=100, n_items=30, pop_size=20,
              cso_cat_data=None):
        """Bắt đầu animation. Chỉ gọi từ _on_single_done."""
        self.stop()

        try:    self._history = [float(x) for x in history_best]
        except: self._history = []

        self._best_solution_chrom = []
        if best_solution is not None:
            try:
                self._best_solution_chrom = [1 if bool(x) else 0
                                             for x in best_solution]
            except: pass

        self._algorithm = str(algorithm)
        try:    self._n_items  = max(1, int(n_items))
        except: self._n_items  = 30
        try:    self._pop_size = max(1, int(pop_size))
        except: self._pop_size = 20

        # Giới hạn tổng animation ≤ 5000ms
        n_frames = len(self._history)
        MAX_MS   = 5000
        try:    raw_ms = max(10, int(speed_ms))
        except: raw_ms = 100
        if n_frames > 0:
            self._speed_ms = max(10, min(raw_ms, MAX_MS // n_frames))
        else:
            self._speed_ms = raw_ms

        self._pan_x = 0.0; self._pan_y = 0.0
        self._scale = 1.0

        # Build data
        if self._algorithm == "CSO":
            self._build_cso_frames(cso_cat_data)
            self._setup_3d_panel()
        else:
            self._build_populations()
            self._teardown_3d_panel()
            self._auto_zoom_ga()   # zoom để nhìn thấy hết

        # Best-bar
        self._build_best_bar_panel()

        self._current_gen = 0
        self._running     = True
        self._tick()

    def stop(self):
        self._running = False
        if self._anim_id:
            try: self.after_cancel(self._anim_id)
            except: pass
            self._anim_id = None
        self._stop_3d_rotation()

    def replay(self):
        """Chạy lại animation từ đầu với dữ liệu hiện tại (không rebuild)."""
        if not self._history:
            return
        self.stop()
        self._current_gen = 0
        self._running     = True
        self._tick()
        if self._algorithm == "CSO":
            self._start_3d_rotation()

    # ══════════════════════════  LAYOUT HELPERS  ══════════════════════════════

    def _build_best_bar_panel(self):
        """Tạo / reset panel mã vạch best chromosome."""
        f = self._best_bar_frame
        # pack lại đảm bảo luôn hiển thị dưới cùng
        f.pack_forget()
        f.pack(in_=self._top_frame, side="bottom", fill="x")
        # pack canvas bên trong
        self._bb_canvas.pack_forget()
        self._bb_canvas.pack(fill="both", expand=True)
        # Vẽ trống ban đầu
        self._draw_best_bar([], 0.0, 0)

    def _setup_3d_panel(self):
        """Tạo panel 3D matplotlib bên phải (chỉ CSO)."""
        if not _HAS_MPL:
            return
        self._teardown_3d_panel()

        w = 260
        f = tk.Frame(self._top_frame, bg=C_BG, width=w,
                     highlightbackground=C_PANEL_BDR,
                     highlightthickness=1)
        f.pack(side="right", fill="y", padx=(4, 0))
        f.pack_propagate(False)
        self._panel3d_frame = f

        # Header label
        tk.Label(f, text="3D Fitness Landscape",
                 font=("Segoe UI", 8, "bold"),
                 bg=C_BG, fg=C_TEXT).pack(pady=(6, 0))

        # Figure
        fig = plt.Figure(figsize=(2.6, 2.6), dpi=90, facecolor=C_BG)
        ax  = fig.add_subplot(111, projection="3d")
        ax.set_facecolor(C_BG)
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self._fig3d = fig
        self._ax3d  = ax

        # Vẽ bề mặt Sphere-like (2 chiều x,y) — đại diện fitness landscape
        self._draw_3d_surface()

        cv = FigureCanvasTkAgg(fig, master=f)
        cv.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)
        cv.draw()
        self._canvas3d = cv

        # Thêm label hướng dẫn
        tk.Label(f, text="Drag: xoay  •  Auto-rotating",
                 font=("Segoe UI", 7), bg=C_BG, fg=C_TEXT_DIM).pack(pady=(0, 4))

        # Bind sự kiện drag để xoay thủ công
        widget = cv.get_tk_widget()
        widget.bind("<ButtonPress-1>",   self._3d_drag_start)
        widget.bind("<B1-Motion>",       self._3d_drag_move)
        widget.bind("<ButtonRelease-1>", self._3d_drag_end)
        self._3d_drag_last = None

        self._rot_angle = 30
        self._rot_elev  = 28   # elevation cho xoay dọc
        self._3d_surf   = None  # pre-computed surface object
        self._3d_mesh   = None  # (X,Y,Z) mesh, tính 1 lần
        self._start_3d_rotation()

    def _init_3d_surface(self):
        """Pre-compute mesh + vẽ surface 1 lần duy nhất. Gọi khi setup panel."""
        if self._ax3d is None or not _HAS_MPL:
            return
        ax = self._ax3d
        ax.cla()
        ax.set_facecolor(C_BG)
        N  = 22   # lưới nhỏ hơn → nhanh hơn
        xs = np.linspace(-10, 10, N)
        ys = np.linspace(-10, 10, N)
        X, Y = np.meshgrid(xs, ys)
        Z    = X**2 + Y**2
        self._3d_mesh = (X, Y, Z)
        self._3d_surf = ax.plot_surface(X, Y, Z,
                                        cmap='YlGn', alpha=0.80,
                                        linewidth=0, antialiased=False)
        ax.set_xlabel('x₁', fontsize=7, labelpad=1)
        ax.set_ylabel('x₂', fontsize=7, labelpad=1)
        ax.set_zlabel('f(x)', fontsize=7, labelpad=1)
        ax.tick_params(labelsize=6)
        # Giữ các scatter object để update thay vì vẽ lại
        self._3d_scatters = []

    def _draw_3d_surface(self):
        """Chỉ update góc nhìn và vị trí mèo — KHÔNG vẽ lại surface."""
        if self._ax3d is None:
            return
        ax = self._ax3d

        # Xoá scatter cũ, vẽ scatter mới (nhẹ hơn nhiều so với cla)
        for sc in getattr(self, '_3d_scatters', []):
            try: sc.remove()
            except: pass
        self._3d_scatters = []

        if self._cso_frames and 0 <= self._current_gen < len(self._cso_frames):
            frame = self._cso_frames[self._current_gen]
            for cat in frame.get('cats', []):
                cx = (cat['x'] - 0.5) * 20
                cy = (cat['y'] - 0.5) * 20
                cz = cx**2 + cy**2 + 2
                if cat['is_gbest']:
                    sc = ax.scatter([cx],[cy],[cz], c='#2ecb7e',
                                    s=55, edgecolors='white', linewidths=1.2, depthshade=False)
                elif cat['mode'] == 'trace':
                    sc = ax.scatter([cx],[cy],[cz], c='#4f7dff',
                                    s=25, edgecolors='white', linewidths=0.6,
                                    alpha=0.9, depthshade=False)
                else:
                    sc = ax.scatter([cx],[cy],[cz], c='#ffb347',
                                    s=20, alpha=0.8, depthshade=False)
                self._3d_scatters.append(sc)

        ax.view_init(elev=self._rot_elev, azim=self._rot_angle)

    def _start_3d_rotation(self):
        self._stop_3d_rotation()
        self._init_3d_surface()   # vẽ surface 1 lần
        self._do_rotate_3d()

    def _stop_3d_rotation(self):
        if self._rot_id:
            try: self.after_cancel(self._rot_id)
            except: pass
            self._rot_id = None

    def _do_rotate_3d(self):
        if self._fig3d is None or self._ax3d is None or self._canvas3d is None:
            return
        # Chỉ tự xoay nếu không đang drag
        if not getattr(self, "_3d_dragging", False):
            self._rot_angle = (self._rot_angle + 1.2) % 360
            self._draw_3d_surface()
            try:
                self._canvas3d.draw_idle()
            except Exception:
                return
        self._rot_id = self.after(80, self._do_rotate_3d)

    # ── 3D drag handlers ────────────────────────────────────────────────────
    def _3d_drag_start(self, e):
        self._3d_drag_last = (e.x, e.y)   # lưu cả x và y
        self._3d_dragging  = True

    def _3d_drag_move(self, e):
        if self._3d_drag_last is not None and self._ax3d:
            lx, ly = self._3d_drag_last
            dx = e.x - lx
            dy = e.y - ly
            # Kéo ngang → xoay azimuth; kéo dọc → xoay elevation
            self._rot_angle = (self._rot_angle - dx * 0.7) % 360
            self._rot_elev  = max(-90, min(90, self._rot_elev - dy * 0.5))
            self._draw_3d_surface()
            try: self._canvas3d.draw_idle()
            except: pass
        self._3d_drag_last = (e.x, e.y)

    def _3d_drag_end(self, e):
        self._3d_dragging  = False
        self._3d_drag_last = None

    def _teardown_3d_panel(self):
        self._stop_3d_rotation()
        if self._panel3d_frame:
            try: self._panel3d_frame.destroy()
            except: pass
            self._panel3d_frame = None
        if self._fig3d:
            try: plt.close(self._fig3d)
            except: pass
        self._fig3d = self._ax3d = self._canvas3d = None
        self._3d_surf = self._3d_mesh = None
        self._3d_scatters = []

    # ══════════════════════════  AUTO ZOOM GA  ════════════════════════════════

    def _auto_zoom_ga(self):
        """
        Tính scale để toàn bộ evolution network vừa khít canvas.
        Gọi sau _build_populations() và sau Configure event.
        """
        try:
            W = self._canvas.winfo_width()
            H = self._canvas.winfo_height()
            if W < 10 or H < 10:
                # Chưa render – thử sau
                self.after(60, self._auto_zoom_ga)
                return

            n_gen  = len(self._populations)
            p_size = max(1, self._pop_size)
            COL_W  = 90; COL_H = 34; X_GAP = 120; Y_GAP = 14
            START_X = 40; START_Y = 60

            total_w = START_X + n_gen * (COL_W + X_GAP)
            total_h = START_Y + p_size * (COL_H + Y_GAP)

            sx = (W - 20) / max(1, total_w)
            sy = (H - 20) / max(1, total_h)
            s  = max(0.1, min(1.0, min(sx, sy)))

            self._scale = s
            # căn giữa ngang
            self._pan_x = (W - total_w * s) / 2
            self._pan_y = 10.0
        except Exception as e:
            print("auto_zoom_ga:", e)

    # ══════════════════════════  GA – BUILD DATA  ════════════════════════════

    def _build_populations(self):
        self._populations = []
        self._frame_best_chroms = []
        try:
            rng = random.Random(42)
            n_history = len(self._history)
            prev_best_idx = 0

            for gen, best_val in enumerate(self._history):
                pop = []
                val = float(best_val) if best_val is not None else 0.0
                p_size = max(1, self._pop_size)
                n_it   = max(1, self._n_items)
                is_last_gen = (gen == n_history - 1)
                best_idx = rng.randint(0, p_size - 1)

                for i in range(p_size):
                    fit = val if i == best_idx else val * rng.uniform(0.6, 0.95)

                    chrom = []
                    if i == best_idx and self._best_solution_chrom:
                        chrom = list(self._best_solution_chrom)
                        if len(chrom) < n_it: chrom += [0] * (n_it - len(chrom))
                        chrom = chrom[:n_it]
                        if not is_last_gen:
                            for _ in range(max(1, n_it // 8)):
                                idx = rng.randint(0, n_it - 1)
                                chrom[idx] = 1 - chrom[idx]
                    else:
                        prob = rng.uniform(0.2, 0.8)
                        chrom = [1 if rng.random() < prob else 0
                                 for _ in range(n_it)]

                    parents = []
                    if gen > 0 and p_size > 0:
                        p1 = prev_best_idx if i == best_idx else rng.randint(0, p_size-1)
                        p2 = rng.randint(0, p_size - 1)
                        parents = [p1, p2]

                    pop.append({"fit": fit, "chrom": chrom,
                                "is_best": (i == best_idx), "parents": parents})

                prev_best_idx = best_idx
                self._populations.append(pop)

                # Lưu chrom best của gen này
                best_chrom = pop[best_idx]["chrom"]
                self._frame_best_chroms.append(best_chrom)

        except Exception as e:
            print(f"Lỗi tạo GA data: {e}")

    # ══════════════════════════  CSO – BUILD DATA  ════════════════════════════

    def _build_cso_frames(self, cso_cat_data=None):
        self._cso_frames = []
        self._frame_best_chroms = []
        n_iter  = len(self._history)
        n_cats  = max(4, self._pop_size)
        n_items = max(1, self._n_items)
        rng     = random.Random(99)

        if cso_cat_data:
            for it, frame_data in enumerate(cso_cat_data):
                cats_out = []
                best_fit = self._history[min(it, n_iter-1)] if self._history else 0.0
                gbest_chrom = []
                for c in frame_data.get("cats", []):
                    cat_dict = {
                        "x"       : float(c.get("x", rng.random())),
                        "y"       : float(c.get("y", rng.random())),
                        "fit"     : float(c.get("fit", best_fit)),
                        "mode"    : c.get("mode", "seek"),
                        "is_gbest": bool(c.get("is_gbest", False)),
                        "chrom"   : list(c.get("chrom", [])),
                    }
                    cats_out.append(cat_dict)
                    if cat_dict["is_gbest"]:
                        gbest_chrom = cat_dict["chrom"]
                self._cso_frames.append({
                    "iteration": it,
                    "best_fit" : best_fit,
                    "cats"     : cats_out,
                })
                self._frame_best_chroms.append(gbest_chrom or self._best_solution_chrom)
        else:
            cat_positions  = [(rng.random(), rng.random()) for _ in range(n_cats)]
            cat_velocities = [(rng.uniform(-0.04, 0.04),
                               rng.uniform(-0.04, 0.04)) for _ in range(n_cats)]
            cat_fit   = [rng.uniform(0.3, 0.9) for _ in range(n_cats)]
            cat_chroms = []
            for _ in range(n_cats):
                p = rng.uniform(0.2, 0.8)
                cat_chroms.append([1 if rng.random() < p else 0
                                   for _ in range(n_items)])

            gbest_idx = int(max(range(n_cats), key=lambda i: cat_fit[i]))
            gbest_pos = cat_positions[gbest_idx]
            MR = 0.2

            for it in range(n_iter):
                best_fit = self._history[it]
                modes = ["trace" if rng.random() < MR else "seek"
                         for _ in range(n_cats)]

                new_positions  = list(cat_positions)
                new_velocities = list(cat_velocities)
                new_fit        = list(cat_fit)
                new_chroms     = [list(c) for c in cat_chroms]

                for i in range(n_cats):
                    x, y   = cat_positions[i]
                    vx, vy = cat_velocities[i]

                    if modes[i] == "trace":
                        gx, gy = gbest_pos
                        c1 = rng.uniform(1.05, 2.05)
                        r  = rng.random()
                        vx = max(-0.12, min(0.12, vx + c1*r*(gx - x)))
                        vy = max(-0.12, min(0.12, vy + c1*r*(gy - y)))
                        nx = max(0.05, min(0.95, x + vx))
                        ny = max(0.05, min(0.95, y + vy))
                        new_velocities[i] = (vx, vy)
                        if self._best_solution_chrom and it == n_iter - 1:
                            bc = list(self._best_solution_chrom)
                            if len(bc) < n_items: bc += [0]*(n_items-len(bc))
                            new_chroms[i] = bc[:n_items]
                        else:
                            for bit in range(n_items):
                                if rng.random() < 0.15:
                                    new_chroms[i][bit] = 1 - new_chroms[i][bit]
                    else:
                        SMP = 3
                        best_copy     = (x, y)
                        best_copy_fit = new_fit[i]
                        for _ in range(SMP):
                            cx_ = max(0.05, min(0.95, x + rng.uniform(-0.15, 0.15)))
                            cy_ = max(0.05, min(0.95, y + rng.uniform(-0.15, 0.15)))
                            cf  = min(new_fit[i] * rng.uniform(0.8, 1.15),
                                      best_fit * 1.05)
                            if cf > best_copy_fit:
                                best_copy_fit = cf
                                best_copy = (cx_, cy_)
                        nx, ny = best_copy
                        new_fit[i] = best_copy_fit
                        for bit in range(n_items):
                            if rng.random() < 0.08:
                                new_chroms[i][bit] = 1 - new_chroms[i][bit]

                    new_positions[i] = (nx, ny)

                best_i = int(max(range(n_cats), key=lambda i: new_fit[i]))
                new_fit[best_i] = best_fit
                gbest_idx = best_i
                gbest_pos = new_positions[gbest_idx]
                if self._best_solution_chrom:
                    bc = list(self._best_solution_chrom)
                    if len(bc) < n_items: bc += [0]*(n_items-len(bc))
                    new_chroms[gbest_idx] = bc[:n_items]

                cats_out = []
                for i in range(n_cats):
                    cats_out.append({
                        "x"       : new_positions[i][0],
                        "y"       : new_positions[i][1],
                        "fit"     : new_fit[i],
                        "mode"    : modes[i],
                        "is_gbest": (i == gbest_idx),
                        "chrom"   : new_chroms[i],
                    })

                self._cso_frames.append({
                    "iteration": it,
                    "best_fit" : best_fit,
                    "cats"     : cats_out,
                })
                gbest_chrom = new_chroms[gbest_idx]
                self._frame_best_chroms.append(gbest_chrom)

                cat_positions  = new_positions
                cat_velocities = new_velocities
                cat_fit        = new_fit
                cat_chroms     = new_chroms

    # ══════════════════════════  TICK / DISPATCH  ════════════════════════════

    def _tick(self):
        if not self._running: return
        if self._canvas.winfo_width() < 10:
            self._anim_id = self.after(50, self._tick)
            return
        try:
            if self._algorithm == "CSO":
                self._draw_cso_frame(self._current_gen)
                max_frame = max(0, len(self._cso_frames) - 1)
                # 3D panel tự cập nhật qua _do_rotate_3d loop riêng
            else:
                self._draw_ga_frame(self._current_gen)
                max_frame = max(0, len(self._populations) - 1)

            # Cập nhật best-bar
            if self._current_gen < len(self._frame_best_chroms):
                chrom = self._frame_best_chroms[self._current_gen]
                fit   = (self._history[self._current_gen]
                         if self._current_gen < len(self._history) else 0.0)
                self._draw_best_bar(chrom, fit, self._current_gen)

        except Exception as e:
            print(f"LỖI VẼ FRAME: {e}")
            self._running = False
            return

        if self._current_gen < max_frame:
            self._current_gen += 1
            self._anim_id = self.after(self._speed_ms, self._tick)
        else:
            self._running = False

    # ══════════════════════════  BEST-BAR PANEL  ═════════════════════════════

    def _draw_best_bar(self, chrom: list[int], fit: float, frame_idx: int):
        """Vẽ mã vạch chromosome tốt nhất của frame hiện tại."""
        bc = self._bb_canvas
        try:
            W = bc.winfo_width()
            H = bc.winfo_height() or self.BEST_BAR_H
        except:
            return
        if W < 10:
            return

        bc.delete("all")

        # Nhãn trái
        label = (f"Best  [{self._algorithm}]  "
                 f"frame {frame_idx}  ·  fit={fit:.2f}")
        bc.create_text(8, H//2, text=label,
                       font=("Segoe UI", 8, "bold"),
                       fill=C_TEXT, anchor="w")

        if not chrom:
            return

        # Tính vùng bar
        lbl_w = 220
        bar_x0 = lbl_w
        bar_x1 = W - 10
        bar_w  = max(1, bar_x1 - bar_x0)
        BAR_H  = 20
        bar_y0 = (H - BAR_H) // 2
        bar_y1 = bar_y0 + BAR_H

        n = len(chrom)
        bw = bar_w / max(1, n)

        for bi, bit in enumerate(chrom):
            x0 = bar_x0 + bi * bw
            x1 = x0 + bw * 0.88
            color = C_BAR_1_BEST if bit else C_BAR_0
            bc.create_rectangle(x0, bar_y0, x1, bar_y1,
                                fill=color, outline="")

        # Viền ngoài
        bc.create_rectangle(bar_x0, bar_y0, bar_x1, bar_y1,
                            outline=C_BORDER, fill="", width=1)

        # Nhỏ: số lượng gen = 1
        n_ones = sum(chrom)
        bc.create_text(bar_x1 + 2, H//2,
                       text=f"{n_ones}/{n}",
                       font=("Consolas", 7),
                       fill=C_TEXT_DIM, anchor="w")

    # ══════════════════════════  GA DRAW  ════════════════════════════════════

    def _draw_ga_frame(self, current_gen: int):
        c = self._canvas
        c.delete("all")
        W = c.winfo_width(); H = c.winfo_height()
        if W < 10 or H < 10: return

        s = self._scale; px = self._pan_x; py = self._pan_y
        def tx(x): return x * s + px
        def ty(y): return y * s + py
        def ts(v): return max(1, int(v * s))

        COL_W = 90; COL_H = 34
        X_GAP = 120; Y_GAP = 14
        START_X = 40; START_Y = 60

        # Auto-pan theo gen hiện tại (chỉ khi đang chạy)
        if self._running and self._pan_start is None:
            right_x = START_X + current_gen * (COL_W + X_GAP) + COL_W
            target_px = W - 100 - right_x * s
            if target_px < self._pan_x:
                self._pan_x += (target_px - self._pan_x) * 0.25

        for g in range(current_gen + 1):
            if g >= len(self._populations): continue
            x1 = START_X + g * (COL_W + X_GAP)
            x2 = x1 + COL_W
            if tx(x2) < -100 or tx(x1) > W + 100: continue

            # Dây nối
            if g > 0:
                prev_x2 = START_X + (g-1) * (COL_W + X_GAP) + COL_W
                for ci, ind in enumerate(self._populations[g]):
                    y2 = START_Y + ci * (COL_H + Y_GAP) + COL_H / 2
                    for p_i in ind.get("parents", []):
                        if p_i >= len(self._populations[g-1]): continue
                        y1 = START_Y + p_i * (COL_H + Y_GAP) + COL_H / 2
                        is_bl = (ind.get("is_best") and
                                 self._populations[g-1][p_i].get("is_best"))
                        c.create_line(tx(prev_x2), ty(y1), tx(x1), ty(y2),
                                      fill=C_LINE_BEST if is_bl else C_LINE,
                                      width=ts(2 if is_bl else 1))

            c.create_text(tx(x1 + COL_W/2), ty(START_Y - 20),
                          text=f"Gen {g}",
                          font=("Segoe UI", max(8, ts(9)), "bold"),
                          fill=C_TEXT)

            for i, ind in enumerate(self._populations[g]):
                y1 = START_Y + i * (COL_H + Y_GAP)
                y2 = y1 + COL_H
                if ty(y2) < -100 or ty(y1) > H + 100: continue
                is_best = ind.get("is_best", False)
                self._rrect(tx(x1), ty(y1), tx(x2), ty(y2), r=ts(4),
                            fill=C_NODE_BEST if is_best else C_NODE_BG,
                            outline=C_BAR_1_BEST if is_best else C_BORDER)
                c.create_text(tx(x1+6), ty(y1+10),
                              text=f"Fit:{ind.get('fit',0):.1f}",
                              font=("Consolas", max(6, ts(7)),
                                    "bold" if is_best else "normal"),
                              fill=C_BAR_1_BEST if is_best else C_TEXT_DIM,
                              anchor="w")
                bar_y1 = y1 + 20; bar_y2 = y2 - 6
                total_bar_w = COL_W - 12
                w_per_bar   = total_bar_w / max(1, self._n_items)
                for bit_idx, bit in enumerate(ind.get("chrom", [])):
                    bx1_ = x1 + 6 + bit_idx * w_per_bar
                    bx2_ = bx1_ + w_per_bar * 0.75
                    bc_  = (C_BAR_1_BEST if is_best else C_BAR_1) if bit else C_BAR_0
                    c.create_rectangle(tx(bx1_), ty(bar_y1),
                                       tx(bx2_), ty(bar_y2),
                                       fill=bc_, outline="")

        title = (f"GA  |  Gen {current_gen}/"
                 f"{max(0, len(self._populations)-1)}"
                 f"  [scroll chuột=zoom, kéo phải=pan]")
        c.create_text(12, 16, text=title,
                      font=("Segoe UI", 10, "bold"),
                      fill=C_TEXT, anchor="w")

    # ══════════════════════════  CSO DRAW  ═══════════════════════════════════

    def _draw_cso_frame(self, frame_idx: int):
        c = self._canvas
        c.delete("all")
        W = c.winfo_width(); H = c.winfo_height()
        if W < 10 or H < 10: return
        if not self._cso_frames: return

        frame_idx = max(0, min(frame_idx, len(self._cso_frames) - 1))
        frame     = self._cso_frames[frame_idx]

        MARGIN   = 52
        LEGEND_H = 44
        plot_x0  = MARGIN
        plot_y0  = MARGIN + 28
        plot_x1  = W - MARGIN
        plot_y1  = H - MARGIN - LEGEND_H
        plot_w   = max(10, plot_x1 - plot_x0)
        plot_h   = max(10, plot_y1 - plot_y0)

        def to_px(nx, ny):
            return plot_x0 + nx * plot_w, plot_y0 + ny * plot_h

        # 1. Nền & lưới
        c.create_rectangle(plot_x0, plot_y0, plot_x1, plot_y1,
                           fill="#f8faff", outline=C_BORDER, width=1)
        for gi in range(1, 6):
            t = gi / 6
            gx = plot_x0 + t * plot_w
            gy = plot_y0 + t * plot_h
            c.create_line(gx, plot_y0, gx, plot_y1,
                          fill=C_GRID, width=1, dash=(4, 4))
            c.create_line(plot_x0, gy, plot_x1, gy,
                          fill=C_GRID, width=1, dash=(4, 4))

        # 2. Trục nhãn
        c.create_text(plot_x0 + plot_w//2, plot_y1 + 16,
                      text="Dim-1 (X₁)",
                      font=("Segoe UI", 8), fill=C_TEXT_DIM)
        c.create_text(plot_x0 - 30, plot_y0 + plot_h//2,
                      text="Dim-2\n(X₂)",
                      font=("Segoe UI", 8), fill=C_TEXT_DIM)

        cats   = frame.get("cats", [])
        n_cats = len(cats)
        if n_cats == 0: return

        # 3. Vòng tìm kiếm cho seeking cats (nhỏ hơn)
        SEEK_RADIUS = 0.08
        for cat in cats:
            if cat["mode"] == "seek" and not cat["is_gbest"]:
                cx, cy = to_px(cat["x"], cat["y"])
                rx = SEEK_RADIUS * plot_w
                ry = SEEK_RADIUS * plot_h
                c.create_oval(cx-rx, cy-ry, cx+rx, cy+ry,
                              outline=C_SEEK_BODY, fill="",
                              width=1, dash=(3, 5))

        # 4. Đường kết nối tracing → gbest
        gbest_cat = next((ct for ct in cats if ct["is_gbest"]), None)
        if gbest_cat:
            gx, gy = to_px(gbest_cat["x"], gbest_cat["y"])
            for cat in cats:
                if cat["mode"] == "trace" and not cat["is_gbest"]:
                    cx, cy = to_px(cat["x"], cat["y"])
                    c.create_line(cx, cy, gx, gy,
                                  fill=C_TRACE_BODY, width=1,
                                  dash=(6, 4), arrow="last",
                                  arrowshape=(6, 8, 3))

        # 5. Vẽ mèo — nhỏ hơn và spacing tốt hơn
        # Bán kính nhỏ hơn so với trước (max 16 thay vì 26)
        BASE_R = max(8, min(16, int(260 / max(8, n_cats))))

        for cat in cats:
            cx, cy = to_px(cat["x"], cat["y"])
            r        = BASE_R
            mode     = cat["mode"]
            is_gbest = cat["is_gbest"]

            if is_gbest:
                body_c   = C_TRACE_BEST
                border_c = "#1a9962"
                border_w = 2
            elif mode == "trace":
                body_c   = C_TRACE_BODY
                border_c = "#2244cc"
                border_w = 2
            else:
                body_c   = C_SEEK_BODY
                border_c = "#cc6600"
                border_w = 1

            # Vòng sáng gbest
            if is_gbest:
                c.create_oval(cx-r-6, cy-r-6, cx+r+6, cy+r+6,
                              outline=C_GBEST_RING, width=2,
                              fill="#e8fff4", dash=(4, 3))

            # Thân (oval đứng)
            c.create_oval(cx-r, cy-r+3, cx+r, cy+r+3,
                          fill=body_c, outline=border_c, width=border_w)

            # Tai
            eh = max(5, r//2); ew = max(3, r//3)
            c.create_polygon(cx-r+2,       cy-r+3,
                             cx-r+2+ew,    cy-r+3-eh,
                             cx-r+2+ew*2,  cy-r+3,
                             fill=border_c, outline="")
            c.create_polygon(cx+r-2,       cy-r+3,
                             cx+r-2-ew,    cy-r+3-eh,
                             cx+r-2-ew*2,  cy-r+3,
                             fill=border_c, outline="")

            # Mắt
            ey  = cy - r//4 + 3
            eof = r // 3
            for ex in (cx - eof, cx + eof):
                c.create_oval(ex-2, ey-2, ex+2, ey+2,
                              fill="white", outline=border_c)
                c.create_oval(ex-1, ey-1, ex+1, ey+1,
                              fill="#111", outline="")

            # Đuôi
            tbx = cx + r - 2; tby = cy + r//2 + 3
            if mode == "trace":
                c.create_line(tbx, tby, tbx+r, tby-r//2,
                              fill=border_c, width=2, smooth=True)
            else:
                c.create_line(tbx, tby,
                              tbx+r//2, tby+r//2,
                              tbx+r,    tby,
                              fill=border_c, width=2, smooth=True)

            # Fitness label
            c.create_text(cx, cy+r+12,
                          text=f"{cat['fit']:.1f}",
                          font=("Consolas", 7,
                                "bold" if is_gbest else "normal"),
                          fill="#1a9962" if is_gbest else C_TEXT_DIM)

            # Badge
            badge = ("★BEST" if is_gbest
                     else ("TRC" if mode == "trace" else "SEK"))
            badge_bg = (C_GBEST_RING if is_gbest
                        else (C_TRACE_BODY if mode == "trace" else C_SEEK_BODY))
            bw2 = 34; bh2 = 13
            c.create_rectangle(cx-bw2//2, cy-r-16,
                               cx+bw2//2, cy-r-3,
                               fill=badge_bg, outline="")
            c.create_text(cx, cy-r-9, text=badge,
                          font=("Segoe UI", 6, "bold"), fill="white")

        # 6. Thống kê
        n_seek  = sum(1 for ct in cats if ct["mode"] == "seek")
        n_trace = sum(1 for ct in cats if ct["mode"] == "trace")

        # 7. Tiêu đề
        title = (f"CSO  |  Iter {frame_idx}/{max(0,len(self._cso_frames)-1)}"
                 f"  ·  Best Fit: {frame['best_fit']:.1f}"
                 f"  ·  Cats: {n_cats}")
        c.create_text(plot_x0, 14, text=title,
                      font=("Segoe UI", 10, "bold"),
                      fill=C_TEXT, anchor="w")

        # 8. Legend
        ly = H - LEGEND_H + 6
        items = [
            (C_SEEK_BODY,  "#cc6600", f"Seeking ({n_seek})"),
            (C_TRACE_BODY, "#2244cc", f"Tracing ({n_trace})"),
            (C_TRACE_BEST, "#1a9962", "Global Best"),
        ]
        lx = MARGIN
        for bc_, oc, lbl in items:
            c.create_oval(lx, ly+2, lx+12, ly+14,
                          fill=bc_, outline=oc, width=2)
            c.create_text(lx+17, ly+8, text=lbl,
                          font=("Segoe UI", 8),
                          fill=C_TEXT, anchor="w")
            lx += 140

    # ══════════════════════════  PAN / ZOOM / RESIZE  ════════════════════════

    def _on_pan_start(self, e):
        self._pan_start = (e.x - self._pan_x, e.y - self._pan_y)

    def _on_pan_move(self, e):
        if self._pan_start:
            self._pan_x = e.x - self._pan_start[0]
            self._pan_y = e.y - self._pan_start[1]
            if not self._running:
                if self._algorithm == "CSO":
                    self._draw_cso_frame(self._current_gen)
                else:
                    self._draw_ga_frame(self._current_gen)

    def _on_pan_end(self, e):
        self._pan_start = None

    def _on_scroll(self, e):
        if self._algorithm == "CSO":
            return
        factor = 1.1 if (getattr(e, "delta", 0) > 0 or e.num == 4) else 0.9
        mx = e.x; my = e.y
        self._pan_x = mx - (mx - self._pan_x) * factor
        self._pan_y = my - (my - self._pan_y) * factor
        self._scale = max(0.08, min(3.0, self._scale * factor))
        if not self._running:
            self._draw_ga_frame(self._current_gen)

    def _on_resize(self, e):
        if self._algorithm == "GA" and not self._running and self._populations:
            # Recompute auto zoom khi cửa sổ thay đổi kích thước
            self._auto_zoom_ga()
        if not self._running:
            if self._algorithm == "CSO":
                self._draw_cso_frame(self._current_gen)
            else:
                self._draw_ga_frame(self._current_gen)

    # ══════════════════════════  UTIL  ═══════════════════════════════════════

    def _rrect(self, x1, y1, x2, y2, r=4, **kw):
        x1, y1, x2, y2 = float(x1), float(y1), float(x2), float(y2)
        if x2 < x1: x1, x2 = x2, x1
        if y2 < y1: y1, y2 = y2, y1
        r = float(max(0, min(r, (x2-x1)/2, (y2-y1)/2)))
        pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r,
               x2,y2-r, x2,y2, x2-r,y2, x1+r,y2,
               x1,y2, x1,y2-r, x1,y1+r, x1,y1, x1+r,y1]
        self._canvas.create_polygon(pts, smooth=True, **kw)