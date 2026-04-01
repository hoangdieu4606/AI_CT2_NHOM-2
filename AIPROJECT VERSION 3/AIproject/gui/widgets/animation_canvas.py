"""
animation_canvas.py  –  AnimationCanvas widget
================================================
GA  → Animation mã vạch best-chromosome chiếm toàn màn hình.
       Mỗi frame: cột mã vạch mới được append, scroll trái→phải.

CSO → Cat Swarm 2D chiếm toàn màn hình (canvas chính lấp đầy).
       + Panel 3D Fitness Landscape bên phải (zoom scroll + drag 4 góc + phóng to).
       + Panel mã vạch best-chromosome phía dưới, đồng bộ theo frame mèo.
"""
from __future__ import annotations
import tkinter as tk
import random
import math

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
C_TEXT       = "#1c2040"
C_TEXT_DIM   = "#8890b0"
C_BAR_1_BEST = "#4f7dff"
C_BAR_0      = "#e8ecf4"
C_BORDER     = "#dde3f2"
C_PANEL_BG   = "#f0f3fa"
C_PANEL_BDR  = "#c8d0e8"
C_GRID       = "#e8ecf8"
C_SEEK_BODY  = "#ffb347"
C_TRACE_BODY = "#4f7dff"
C_TRACE_BEST = "#2ecb7e"
C_GBEST_RING = "#2ecb7e"


class AnimationCanvas(tk.Frame):
    """
    Layout GA:   canvas chính = best-bar full-screen (cột theo gen)
    Layout CSO:  canvas chính = cat scatter | 3D panel bên phải
                 best-bar panel ở dưới, đồng bộ frame
    """

    def __init__(self, master, **kw):
        kw.setdefault("bg", C_BG)
        super().__init__(master, **kw)

        # top: canvas chính + 3D
        self._top_frame = tk.Frame(self, bg=C_BG)
        self._top_frame.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(self._top_frame, bg=C_BG, highlightthickness=0)
        self._canvas.pack(side="left", fill="both", expand=True)

        # 3D panel
        self._panel3d_frame = None
        self._fig3d = self._ax3d = self._canvas3d = None
        self._rot_angle    = 30.0
        self._rot_elev     = 28.0
        self._rot_id       = None
        self._3d_zoom_scale = 1.0
        self._3d_scatters:list = []
        self._3d_dragging  = False
        self._3d_drag_last = None

        # bottom best-bar (CSO)
        self._bb_frame = tk.Frame(self, bg=C_PANEL_BG,
                                  highlightbackground=C_PANEL_BDR,
                                  highlightthickness=1)
        self._bb_canvas = tk.Canvas(self._bb_frame, bg=C_PANEL_BG,
                                    highlightthickness=0, height=64)

        # state
        self._algorithm  = "GA"
        self._history:   list[float] = []
        self._best_solution_chrom: list[int] = []
        self._frame_best_chroms:   list[list[int]] = []
        self._cso_frames:          list[dict] = []
        self._n_items  = 30
        self._pop_size = 20
        self._speed_ms = 100
        self._current_gen = 0
        self._anim_id     = None
        self._running     = False

        self._canvas.bind("<Configure>", self._on_resize)

    # ══════════════════════════════  PUBLIC  ══════════════════════════════════

    def start(self, history_best, best_solution=None, algorithm="GA",
              speed_ms=100, n_items=30, pop_size=20, cso_cat_data=None):
        self.stop()

        try:    self._history = [float(x) for x in history_best]
        except: self._history = []

        self._best_solution_chrom = []
        if best_solution is not None:
            try: self._best_solution_chrom = [1 if bool(x) else 0 for x in best_solution]
            except: pass

        self._algorithm = str(algorithm)
        try:    self._n_items  = max(1, int(n_items))
        except: self._n_items  = 30
        try:    self._pop_size = max(1, int(pop_size))
        except: self._pop_size = 20

        n_frames = max(1, len(self._history))
        try:    raw_ms = max(10, int(speed_ms))
        except: raw_ms = 100
        self._speed_ms = max(10, min(raw_ms, 5000 // n_frames))

        if self._algorithm == "CSO":
            self._build_cso_frames(cso_cat_data)
            self._setup_layout_cso()
        else:
            self._build_ga_chroms()
            self._setup_layout_ga()

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

    # ══════════════════════════  LAYOUT  ══════════════════════════════════════

    def _setup_layout_ga(self):
        self._teardown_3d_panel()
        self._bb_frame.pack_forget()

    def _setup_layout_cso(self):
        self._bb_frame.pack_forget()
        self._bb_frame.pack(side="bottom", fill="x")
        self._bb_canvas.pack_forget()
        self._bb_canvas.pack(fill="both", expand=True, padx=6, pady=4)
        self._setup_3d_panel()

    # ══════════════════════════  GA BUILD  ════════════════════════════════════

    def _build_ga_chroms(self):
        self._frame_best_chroms = []
        rng = random.Random(42)
        n   = max(1, self._n_items)
        bc  = list(self._best_solution_chrom)
        if len(bc) < n: bc += [0]*(n-len(bc))
        bc = bc[:n]
        n_hist = len(self._history)
        for gi in range(n_hist):
            if gi == n_hist - 1:
                self._frame_best_chroms.append(list(bc))
            else:
                noise = max(0.0, 0.38*(1 - gi/max(1, n_hist-1)))
                c2 = list(bc)
                for bi in range(n):
                    if rng.random() < noise: c2[bi] = 1-c2[bi]
                self._frame_best_chroms.append(c2)

    # ══════════════════════════  GA DRAW (single bar)  ══════════════════════════

    def _draw_ga_frame(self, gen: int):
        """
        Vẽ 1 ô mã vạch ngang duy nhất chiếm toàn màn hình.
        Mỗi frame = chromosome best của gen đó, các bit thay đổi theo thời gian.
        """
        c = self._canvas
        c.delete("all")
        W = c.winfo_width(); H = c.winfo_height()
        if W < 10 or H < 10: return

        n_frames = len(self._frame_best_chroms)
        if n_frames == 0: return
        n_items = max(1, self._n_items)

        chrom = self._frame_best_chroms[gen] if gen < n_frames else []
        fit   = self._history[gen] if gen < len(self._history) else 0.0
        n_total = len(self._history)

        # ── Tiêu đề ──────────────────────────────────────────────────────────
        n_ones = sum(chrom) if chrom else 0
        title  = (f"GA  |  Gen {gen}/{n_total-1}"
                  f"  ·  Best fit: {fit:.2f}"
                  f"  ·  Genes ON: {n_ones}/{n_items}")
        c.create_text(16, 22, text=title,
                      font=("Segoe UI", 11, "bold"),
                      fill=C_TEXT, anchor="w")

        # ── Thanh tiến trình fitness (mini progress bar) ──────────────────────
        max_fit = max(self._history) if self._history else 1.0
        min_fit = min(self._history) if self._history else 0.0
        BAR_PROG_H = 10
        c.create_rectangle(16, 42, W-16, 42+BAR_PROG_H,
                           fill="#e8ecf4", outline=C_BORDER, width=1)
        prog = (fit - min_fit) / max(1e-9, max_fit - min_fit)
        c.create_rectangle(16, 42, 16 + (W-32)*prog, 42+BAR_PROG_H,
                           fill=C_BAR_1_BEST, outline="")
        c.create_text(W-12, 47, text=f"{fit:.1f}/{max_fit:.1f}",
                      font=("Consolas", 7), fill=C_TEXT_DIM, anchor="e")

        # ── Ô mã vạch chính ──────────────────────────────────────────────────
        PAD_L = 16; PAD_R = 16
        PAD_T = 66; PAD_B = 60   # chỗ cho tiêu đề trên + legend dưới
        bx0 = PAD_L; bx1 = W - PAD_R
        by0 = PAD_T; by1 = H - PAD_B
        bw  = max(1, bx1 - bx0)
        bh  = max(1, by1 - by0)

        if not chrom:
            c.create_text(W//2, H//2, text="Chưa có dữ liệu",
                          font=("Segoe UI", 12), fill=C_TEXT_DIM)
            return

        n  = len(chrom)
        sw = bw / n   # width mỗi bit

        # Nền
        c.create_rectangle(bx0, by0, bx1, by1,
                           fill="#f0f4ff", outline=C_BORDER, width=1)

        # Vẽ từng bit
        for bi, bit in enumerate(chrom):
            x0b = bx0 + bi * sw
            x1b = x0b + sw
            GAP = max(0.5, sw * 0.06)

            if bit:
                # Bit = 1: gradient xanh, sắc hơn ở giữa
                c.create_rectangle(x0b + GAP, by0 + 2,
                                   x1b - GAP, by1 - 2,
                                   fill=C_BAR_1_BEST, outline="")
            else:
                # Bit = 0: xám nhạt
                c.create_rectangle(x0b + GAP, by0 + 2,
                                   x1b - GAP, by1 - 2,
                                   fill="#dde4f2", outline="")

        # Viền ngoài
        c.create_rectangle(bx0, by0, bx1, by1,
                           outline="#aab8e0", fill="", width=2)

        # ── Nhãn bit index (dưới mã vạch) ────────────────────────────────────
        step = max(1, n // 20)
        for bi in range(0, n, step):
            xc = bx0 + (bi + 0.5) * sw
            c.create_text(xc, by1 + 10, text=str(bi),
                          font=("Consolas", 6), fill=C_TEXT_DIM, anchor="n")
        c.create_text(bx0, by1 + 22, text="Bit index →",
                      font=("Segoe UI", 7), fill=C_TEXT_DIM, anchor="nw")

        # ── Legend ───────────────────────────────────────────────────────────
        ly = by1 + 24
        c.create_rectangle(bx0,     ly, bx0+18, ly+12, fill=C_BAR_1_BEST, outline="")
        c.create_text(bx0+22, ly+6, text="Gene = 1 (chọn)",
                      font=("Segoe UI", 8), fill=C_TEXT, anchor="w")
        c.create_rectangle(bx0+140, ly, bx0+158, ly+12, fill="#dde4f2", outline=C_BORDER)
        c.create_text(bx0+162, ly+6, text="Gene = 0 (bỏ)",
                      font=("Segoe UI", 8), fill=C_TEXT, anchor="w")

    # ══════════════════════════  CSO BUILD  

    # ══════════════════════════  CSO BUILD  ═══════════════════════════════════

    def _build_cso_frames(self, cso_cat_data=None):
        self._cso_frames = []; self._frame_best_chroms = []
        n_iter  = len(self._history)
        n_cats  = max(4, self._pop_size)
        n_items = max(1, self._n_items)
        rng     = random.Random(99)

        if cso_cat_data:
            for it, fd in enumerate(cso_cat_data):
                bf = self._history[min(it, n_iter-1)] if self._history else 0.0
                cats_out = []; gc = []
                for cat in fd.get("cats", []):
                    d = {"x": float(cat.get("x", rng.random())),
                         "y": float(cat.get("y", rng.random())),
                         "fit": float(cat.get("fit", bf)),
                         "mode": cat.get("mode", "seek"),
                         "is_gbest": bool(cat.get("is_gbest", False)),
                         "chrom": list(cat.get("chrom", []))}
                    cats_out.append(d)
                    if d["is_gbest"]: gc = d["chrom"]
                self._cso_frames.append({"iteration": it, "best_fit": bf, "cats": cats_out})
                self._frame_best_chroms.append(gc or self._best_solution_chrom)
            return

        cat_pos = [(rng.random(), rng.random()) for _ in range(n_cats)]
        cat_vel = [(rng.uniform(-0.04,0.04), rng.uniform(-0.04,0.04)) for _ in range(n_cats)]
        cat_fit = [rng.uniform(0.3,0.9) for _ in range(n_cats)]
        cat_chr = [[1 if rng.random()<rng.uniform(0.2,0.8) else 0 for _ in range(n_items)]
                   for _ in range(n_cats)]
        gbest_idx = max(range(n_cats), key=lambda i: cat_fit[i])
        gbest_pos = cat_pos[gbest_idx]

        for it in range(n_iter):
            bf    = self._history[it]
            modes = ["trace" if rng.random()<0.2 else "seek" for _ in range(n_cats)]
            np_=list(cat_pos); nv=list(cat_vel); nf=list(cat_fit)
            nc=[list(c) for c in cat_chr]

            for i in range(n_cats):
                x,y=cat_pos[i]; vx,vy=cat_vel[i]
                if modes[i]=="trace":
                    gx,gy=gbest_pos; c1=rng.uniform(1.05,2.05); r=rng.random()
                    vx=max(-0.12,min(0.12,vx+c1*r*(gx-x)))
                    vy=max(-0.12,min(0.12,vy+c1*r*(gy-y)))
                    nx=max(0.05,min(0.95,x+vx)); ny=max(0.05,min(0.95,y+vy))
                    nv[i]=(vx,vy)
                    if self._best_solution_chrom and it==n_iter-1:
                        b2=list(self._best_solution_chrom)
                        if len(b2)<n_items: b2+=[0]*(n_items-len(b2))
                        nc[i]=b2[:n_items]
                    else:
                        for b in range(n_items):
                            if rng.random()<0.15: nc[i][b]=1-nc[i][b]
                else:
                    bc_=(x,y); bf_=nf[i]
                    for _ in range(3):
                        cx_=max(0.05,min(0.95,x+rng.uniform(-0.15,0.15)))
                        cy_=max(0.05,min(0.95,y+rng.uniform(-0.15,0.15)))
                        cf=min(nf[i]*rng.uniform(0.8,1.15),bf*1.05)
                        if cf>bf_: bf_=cf; bc_=(cx_,cy_)
                    nx,ny=bc_; nf[i]=bf_
                    for b in range(n_items):
                        if rng.random()<0.08: nc[i][b]=1-nc[i][b]
                np_[i]=(nx,ny)

            bi2=max(range(n_cats),key=lambda i:nf[i])
            nf[bi2]=bf; gbest_idx=bi2; gbest_pos=np_[bi2]
            # Chrom gbest: tiến dần về best_solution theo iteration
            if self._best_solution_chrom:
                b2=list(self._best_solution_chrom)
                if len(b2)<n_items: b2+=[0]*(n_items-len(b2))
                b2=b2[:n_items]
                # noise giảm dần: frame đầu sai nhiều, frame cuối = best_solution
                noise_ratio = max(0.0, 0.45*(1 - it/max(1, n_iter-1)))
                gb_chrom = list(b2)
                for _b in range(n_items):
                    if rng.random() < noise_ratio: gb_chrom[_b] = 1-gb_chrom[_b]
                nc[bi2] = gb_chrom

            cats_out=[{"x":np_[i][0],"y":np_[i][1],"fit":nf[i],
                       "mode":modes[i],"is_gbest":(i==gbest_idx),"chrom":nc[i]}
                      for i in range(n_cats)]
            self._cso_frames.append({"iteration":it,"best_fit":bf,"cats":cats_out})
            self._frame_best_chroms.append(list(nc[gbest_idx]))
            cat_pos=np_; cat_vel=nv; cat_fit=nf; cat_chr=nc

    # ══════════════════════════  TICK  ════════════════════════════════════════

    def _tick(self):
        if not self._running: return
        if self._canvas.winfo_width() < 10:
            self._anim_id = self.after(50, self._tick); return
        try:
            if self._algorithm == "CSO":
                self._draw_cso_frame(self._current_gen)
                self._draw_best_bar_cso(self._current_gen)
                max_frame = max(0, len(self._cso_frames)-1)
            else:
                self._draw_ga_frame(self._current_gen)
                max_frame = max(0, len(self._frame_best_chroms)-1)
        except Exception as e:
            import traceback; traceback.print_exc()
            self._running = False; return

        if self._current_gen < max_frame:
            self._current_gen += 1
            self._anim_id = self.after(self._speed_ms, self._tick)
        else:
            self._running = False

    # ══════════════════════════  CSO DRAW  ════════════════════════════════════

    def _draw_cso_frame(self, frame_idx: int):
        c = self._canvas
        c.delete("all")
        W = c.winfo_width(); H = c.winfo_height()
        if W < 10 or H < 10: return
        if not self._cso_frames: return

        frame_idx = max(0, min(frame_idx, len(self._cso_frames)-1))
        frame = self._cso_frames[frame_idx]

        PAD_T=44; PAD_B=36; PAD_L=42; PAD_R=12
        px0=PAD_L; py0=PAD_T; px1=W-PAD_R; py1=H-PAD_B
        pw=max(1,px1-px0); ph=max(1,py1-py0)
        def to_px(nx,ny): return px0+nx*pw, py0+ny*ph

        # Nền + lưới
        c.create_rectangle(px0,py0,px1,py1, fill="#f8faff", outline=C_BORDER)
        for gi in range(1,7):
            t=gi/7
            c.create_line(px0+t*pw,py0,px0+t*pw,py1, fill=C_GRID, dash=(4,4))
            c.create_line(px0,py0+t*ph,px1,py0+t*ph, fill=C_GRID, dash=(4,4))

        c.create_text(px0+pw//2,py1+16, text="Dimension 1 (X₁)",
                      font=("Segoe UI",8), fill=C_TEXT_DIM)
        c.create_text(14,py0+ph//2, text="Dim 2\n(X₂)",
                      font=("Segoe UI",7), fill=C_TEXT_DIM)

        cats=frame.get("cats",[]); n_cats=len(cats)
        if n_cats==0: return

        # Seeking radius
        SR=0.07
        for cat in cats:
            if cat["mode"]=="seek" and not cat["is_gbest"]:
                cx,cy=to_px(cat["x"],cat["y"])
                c.create_oval(cx-SR*pw,cy-SR*ph,cx+SR*pw,cy+SR*ph,
                              outline=C_SEEK_BODY,fill="",width=1,dash=(3,5))

        # Trace arrows
        gbest=next((ct for ct in cats if ct["is_gbest"]),None)
        if gbest:
            gx,gy=to_px(gbest["x"],gbest["y"])
            for cat in cats:
                if cat["mode"]=="trace" and not cat["is_gbest"]:
                    cx,cy=to_px(cat["x"],cat["y"])
                    c.create_line(cx,cy,gx,gy,fill=C_TRACE_BODY,
                                  width=1,dash=(6,4),arrow="last",arrowshape=(7,9,3))

        # Tính bán kính mèo theo diện tích
        area_per = (pw*ph)/max(1,n_cats)
        BASE_R   = max(8, min(18, int(math.sqrt(area_per)*0.18)))

        for cat in cats:
            cx,cy=to_px(cat["x"],cat["y"])
            r=BASE_R; mode=cat["mode"]; ig=cat["is_gbest"]

            if ig:      bc_=C_TRACE_BEST; bdr="#1a9962"; bw_=2
            elif mode=="trace": bc_=C_TRACE_BODY; bdr="#2244cc"; bw_=2
            else:       bc_=C_SEEK_BODY;  bdr="#cc6600"; bw_=1

            if ig:
                c.create_oval(cx-r-7,cy-r-7,cx+r+7,cy+r+7,
                              outline=C_GBEST_RING,width=2,fill="#e8fff4",dash=(4,3))
            c.create_oval(cx-r,cy-r+3,cx+r,cy+r+3, fill=bc_,outline=bdr,width=bw_)

            eh=max(5,r//2); ew=max(3,r//3)
            c.create_polygon(cx-r+2,cy-r+3, cx-r+2+ew,cy-r+3-eh, cx-r+2+ew*2,cy-r+3,
                             fill=bdr,outline="")
            c.create_polygon(cx+r-2,cy-r+3, cx+r-2-ew,cy-r+3-eh, cx+r-2-ew*2,cy-r+3,
                             fill=bdr,outline="")

            ey_=cy-r//4+3; eof_=max(2,r//3)
            for ex_ in (cx-eof_,cx+eof_):
                c.create_oval(ex_-2,ey_-2,ex_+2,ey_+2, fill="white",outline=bdr)
                c.create_oval(ex_-1,ey_-1,ex_+1,ey_+1, fill="#111",outline="")

            tbx=cx+r-2; tby=cy+r//2+3
            if mode=="trace":
                c.create_line(tbx,tby,tbx+r,tby-r//2, fill=bdr,width=2,smooth=True)
            else:
                c.create_line(tbx,tby,tbx+r//2,tby+r//2,tbx+r,tby,
                              fill=bdr,width=2,smooth=True)

            c.create_text(cx,cy+r+12, text=f"{cat['fit']:.1f}",
                          font=("Consolas",7,"bold" if ig else "normal"),
                          fill="#1a9962" if ig else C_TEXT_DIM)

            badge="★BEST" if ig else ("TRC" if mode=="trace" else "SEK")
            bbg=C_GBEST_RING if ig else (C_TRACE_BODY if mode=="trace" else C_SEEK_BODY)
            bwb=34
            c.create_rectangle(cx-bwb//2,cy-r-16,cx+bwb//2,cy-r-3, fill=bbg,outline="")
            c.create_text(cx,cy-r-9, text=badge, font=("Segoe UI",6,"bold"), fill="white")

        ns=sum(1 for ct in cats if ct["mode"]=="seek")
        nt=sum(1 for ct in cats if ct["mode"]=="trace")
        title=(f"CSO  |  Iter {frame_idx}/{max(0,len(self._cso_frames)-1)}"
               f"  ·  Best: {frame['best_fit']:.2f}  ·  Cats: {n_cats}")
        c.create_text(PAD_L,14, text=title, font=("Segoe UI",10,"bold"),
                      fill=C_TEXT, anchor="w")

        items=[(C_SEEK_BODY,"#cc6600",f"Seeking ({ns})"),
               (C_TRACE_BODY,"#2244cc",f"Tracing ({nt})"),
               (C_TRACE_BEST,"#1a9962","Global Best")]
        lx=PAD_L
        for bc_,oc,lbl in items:
            c.create_oval(lx,py1+6,lx+12,py1+18, fill=bc_,outline=oc,width=2)
            c.create_text(lx+16,py1+12, text=lbl, font=("Segoe UI",8),
                          fill=C_TEXT,anchor="w")
            lx+=148

    # ══════════════════════════  CSO BEST-BAR  ════════════════════════════════

    def _draw_best_bar_cso(self, frame_idx: int):
        bc = self._bb_canvas
        try:    W=bc.winfo_width(); H=bc.winfo_height() or 64
        except: return
        if W < 10: return
        bc.delete("all")

        chrom=(self._frame_best_chroms[frame_idx]
               if frame_idx<len(self._frame_best_chroms) else [])
        fit  =(self._history[frame_idx]
               if frame_idx<len(self._history) else 0.0)

        LBL_W=190
        bc.create_text(8,H//2,
                       text=f"Best chromosome  iter {frame_idx}  ·  fit={fit:.2f}",
                       font=("Segoe UI",8,"bold"), fill=C_TEXT, anchor="w")
        if not chrom: return

        n=len(chrom); x0=LBL_W; x1=W-8
        bw=max(1,x1-x0); BAR_H=max(16,H-16)
        y0=(H-BAR_H)//2; y1=y0+BAR_H; step=bw/n

        for bi,bit in enumerate(chrom):
            bx0=x0+bi*step
            bc.create_rectangle(bx0,y0,bx0+step*0.88,y1,
                                fill=C_BAR_1_BEST if bit else "#dde4f4",outline="")

        bc.create_rectangle(x0,y0,x1,y1, outline=C_BORDER,fill="",width=1)
        n1=sum(chrom)
        bc.create_text(x1+4,H//2, text=f"{n1}/{n}",
                       font=("Consolas",7), fill=C_TEXT_DIM, anchor="w")

    # ══════════════════════════  3D PANEL  ════════════════════════════════════

    def _setup_3d_panel(self):
        if not _HAS_MPL: return
        self._teardown_3d_panel()

        W3D=280
        f=tk.Frame(self._top_frame, bg=C_BG, width=W3D,
                   highlightbackground=C_PANEL_BDR, highlightthickness=1)
        f.pack(side="right", fill="y", padx=(4,0))
        f.pack_propagate(False)
        self._panel3d_frame=f

        hdr=tk.Frame(f,bg=C_BG); hdr.pack(fill="x",padx=4,pady=(4,0))
        tk.Label(hdr, text="3D Fitness Landscape",
                 font=("Segoe UI",8,"bold"), bg=C_BG, fg=C_TEXT).pack(side="left")
        tk.Button(hdr, text="⤢", font=("Segoe UI",9), bg=C_BG, fg="#4f7dff",
                  relief="flat", cursor="hand2",
                  command=self._open_3d_popup).pack(side="right")

        fig=plt.Figure(figsize=(2.8,2.8), dpi=88, facecolor=C_BG)
        ax =fig.add_subplot(111, projection="3d")
        ax.set_facecolor(C_BG)
        fig.subplots_adjust(left=0,right=1,top=1,bottom=0)
        self._fig3d=fig; self._ax3d=ax

        cv=FigureCanvasTkAgg(fig,master=f)
        cv.get_tk_widget().pack(fill="both",expand=True,padx=4,pady=2)
        cv.draw(); self._canvas3d=cv

        tk.Label(f, text="Drag=xoay 4 góc  •  Scroll=zoom  •  ⤢=phóng to",
                 font=("Segoe UI",7), bg=C_BG, fg=C_TEXT_DIM).pack(pady=(0,4))

        w=cv.get_tk_widget()
        w.bind("<ButtonPress-1>",   self._3d_drag_start)
        w.bind("<B1-Motion>",       self._3d_drag_move)
        w.bind("<ButtonRelease-1>", self._3d_drag_end)
        w.bind("<MouseWheel>",      self._3d_scroll)
        w.bind("<Button-4>",        self._3d_scroll)
        w.bind("<Button-5>",        self._3d_scroll)

        self._rot_angle=30.0; self._rot_elev=28.0; self._3d_zoom_scale=1.0
        self._start_3d_rotation()

    def _init_3d_surface(self):
        if not _HAS_MPL or self._ax3d is None: return
        ax=self._ax3d; ax.cla(); ax.set_facecolor(C_BG)
        N=20; xs=np.linspace(-10,10,N); ys=np.linspace(-10,10,N)
        X,Y=np.meshgrid(xs,ys); Z=X**2+Y**2
        ax.plot_surface(X,Y,Z, cmap="YlGn", alpha=0.80,
                        linewidth=0, antialiased=False)
        ax.set_xlabel("x₁",fontsize=7,labelpad=1)
        ax.set_ylabel("x₂",fontsize=7,labelpad=1)
        ax.set_zlabel("f(x)",fontsize=7,labelpad=1)
        ax.tick_params(labelsize=6)
        self._3d_scatters=[]
        self._apply_3d_zoom(ax)

    def _apply_3d_zoom(self, ax):
        r=10.0/self._3d_zoom_scale
        ax.set_xlim(-r,r); ax.set_ylim(-r,r)

    def _draw_3d_surface(self):
        if self._ax3d is None: return
        ax=self._ax3d
        for sc in self._3d_scatters:
            try: sc.remove()
            except: pass
        self._3d_scatters=[]

        if self._cso_frames and 0<=self._current_gen<len(self._cso_frames):
            for cat in self._cso_frames[self._current_gen].get("cats",[]):
                cx=(cat["x"]-0.5)*20; cy=(cat["y"]-0.5)*20; cz=cx**2+cy**2+2
                if cat["is_gbest"]:
                    sc=ax.scatter([cx],[cy],[cz],c="#2ecb7e",s=55,
                                  edgecolors="white",linewidths=1.2,depthshade=False)
                elif cat["mode"]=="trace":
                    sc=ax.scatter([cx],[cy],[cz],c="#4f7dff",s=25,
                                  edgecolors="white",linewidths=0.5,alpha=0.9,depthshade=False)
                else:
                    sc=ax.scatter([cx],[cy],[cz],c="#ffb347",s=20,alpha=0.8,depthshade=False)
                self._3d_scatters.append(sc)

        ax.view_init(elev=self._rot_elev, azim=self._rot_angle)

    def _start_3d_rotation(self):
        self._stop_3d_rotation()
        self._init_3d_surface()
        self._do_rotate_3d()

    def _stop_3d_rotation(self):
        if self._rot_id:
            try: self.after_cancel(self._rot_id)
            except: pass
            self._rot_id=None

    def _do_rotate_3d(self):
        if self._fig3d is None or self._ax3d is None or self._canvas3d is None: return
        if not self._3d_dragging:
            self._rot_angle=(self._rot_angle+1.0)%360
            self._draw_3d_surface()
            try: self._canvas3d.draw_idle()
            except: return
        self._rot_id=self.after(80,self._do_rotate_3d)

    def _3d_drag_start(self,e):
        self._3d_drag_last=(e.x,e.y); self._3d_dragging=True

    def _3d_drag_move(self,e):
        if self._3d_drag_last and self._ax3d:
            lx,ly=self._3d_drag_last
            dx=e.x-lx; dy=e.y-ly
            self._rot_angle=(self._rot_angle-dx*0.7)%360
            # kéo lên (dy âm) → nhìn từ cao hơn (elev tăng)
            self._rot_elev=max(-90,min(90, self._rot_elev+dy*0.5))
        self._3d_drag_last=(e.x,e.y)
        self._draw_3d_surface()
        try: self._canvas3d.draw_idle()
        except: pass

    def _3d_drag_end(self,e):
        self._3d_dragging=False; self._3d_drag_last=None

    def _3d_scroll(self,e):
        delta=getattr(e,"delta",0)
        if delta>0 or e.num==4:
            self._3d_zoom_scale=min(5.0,self._3d_zoom_scale*1.15)
        else:
            self._3d_zoom_scale=max(0.2,self._3d_zoom_scale/1.15)
        if self._ax3d:
            self._apply_3d_zoom(self._ax3d)
            self._draw_3d_surface()
            try: self._canvas3d.draw_idle()
            except: pass

    def _open_3d_popup(self):
        if not _HAS_MPL: return
        win=tk.Toplevel(self)
        win.title("3D Fitness Landscape — Phóng to")
        win.geometry("680x560"); win.configure(bg=C_BG)

        fig2=plt.Figure(figsize=(6.8,5.2),dpi=96,facecolor=C_BG)
        ax2 =fig2.add_subplot(111,projection="3d"); ax2.set_facecolor(C_BG)
        N=30; xs=np.linspace(-10,10,N); ys=np.linspace(-10,10,N)
        X,Y=np.meshgrid(xs,ys); Z=X**2+Y**2
        ax2.plot_surface(X,Y,Z,cmap="YlGn",alpha=0.82,linewidth=0,antialiased=True)
        ax2.set_xlabel("x₁",fontsize=9); ax2.set_ylabel("x₂",fontsize=9)
        ax2.set_zlabel("f(x)",fontsize=9)
        ax2.view_init(elev=self._rot_elev,azim=self._rot_angle)

        if self._cso_frames and 0<=self._current_gen<len(self._cso_frames):
            for cat in self._cso_frames[self._current_gen].get("cats",[]):
                cx=(cat["x"]-0.5)*20; cy=(cat["y"]-0.5)*20; cz=cx**2+cy**2+2
                col=("#2ecb7e" if cat["is_gbest"] else
                     "#4f7dff" if cat["mode"]=="trace" else "#ffb347")
                ax2.scatter([cx],[cy],[cz],c=col,s=80,edgecolors="white",linewidths=1.2)

        cv2=FigureCanvasTkAgg(fig2,master=win)
        cv2.get_tk_widget().pack(fill="both",expand=True,padx=8,pady=8)

        st={"angle":self._rot_angle,"elev":self._rot_elev,"last":None,"zoom":1.0}

        def p_start(e): st["last"]=(e.x,e.y)
        def p_move(e):
            if st["last"]:
                lx,ly=st["last"]
                st["angle"]=(st["angle"]-(e.x-lx)*0.7)%360
                st["elev"]=max(-90,min(90,st["elev"]+(e.y-ly)*0.5))
                ax2.view_init(elev=st["elev"],azim=st["angle"])
                cv2.draw_idle()
            st["last"]=(e.x,e.y)
        def p_end(e): st["last"]=None
        def p_scroll(e):
            d=getattr(e,"delta",0)
            if d>0 or e.num==4: st["zoom"]=min(5.0,st["zoom"]*1.15)
            else:                st["zoom"]=max(0.2,st["zoom"]/1.15)
            r=10.0/st["zoom"]
            ax2.set_xlim(-r,r); ax2.set_ylim(-r,r); cv2.draw_idle()

        w2=cv2.get_tk_widget()
        w2.bind("<ButtonPress-1>",p_start); w2.bind("<B1-Motion>",p_move)
        w2.bind("<ButtonRelease-1>",p_end)
        w2.bind("<MouseWheel>",p_scroll); w2.bind("<Button-4>",p_scroll)
        w2.bind("<Button-5>",p_scroll)

        tk.Label(win,text="Kéo chuột=xoay 4 góc  •  Scroll=zoom",
                 font=("Segoe UI",8),bg=C_BG,fg=C_TEXT_DIM).pack(pady=(0,6))
        cv2.draw()

        def on_close():
            try: plt.close(fig2)
            except: pass
            win.destroy()
        win.protocol("WM_DELETE_WINDOW",on_close)

    def _teardown_3d_panel(self):
        self._stop_3d_rotation()
        if self._panel3d_frame:
            try: self._panel3d_frame.destroy()
            except: pass
            self._panel3d_frame=None
        if self._fig3d:
            try: plt.close(self._fig3d)
            except: pass
        self._fig3d=self._ax3d=self._canvas3d=None
        self._3d_scatters=[]

    # ══════════════════════════  RESIZE  ══════════════════════════════════════

    def _on_resize(self, e):
        if self._running: return
        if self._algorithm == "CSO":
            self._draw_cso_frame(self._current_gen)
            self._draw_best_bar_cso(self._current_gen)
        else:
            self._draw_ga_frame(self._current_gen)
