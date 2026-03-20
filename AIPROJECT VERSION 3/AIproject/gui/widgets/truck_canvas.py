from __future__ import annotations

import math
import tkinter as tk
from typing import Iterable, List

from core.models import KnapsackInstance


BOX_COLORS = [
    "#88c0d0", "#a3be8c", "#ebcb8b", "#d08770", "#b48ead",
    "#5e81ac", "#8fbcbb", "#bf616a", "#81a1c1", "#d8dee9"
]

# Màu viền & text cho chế độ 2D
_BD       = "#2e3440"
_BG_GRID  = "#f5f5f5"
_EMPTY_NO_SOL  = "#e8e8e8"   # ô trống khi chưa có nghiệm
_EMPTY_BD_NO   = "#cccccc"
_EMPTY_HAS_SOL = "#f0f2f8"   # ô trống khi đã có nghiệm (trắng hơn)
_EMPTY_BD_HAS  = "#dde3f2"
_TOGGLE_C = "#4f7dff"   # màu nút toggle
_KG_CELL  = 10          # 10 kg = 1 đơn vị ô


class TruckCanvas(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg="white",
                         highlightthickness=1,
                         highlightbackground="#cccccc", **kwargs)
        self.instance: KnapsackInstance | None = None
        self.solution: List[int] | None        = None
        self._mode = "1d"   # "1d" | "2d"
        self.bind("<Configure>", lambda e: self.redraw())

    # ── public ──────────────────────────────────────────────────────────────
    def set_solution(self, instance: KnapsackInstance,
                     solution: Iterable[int] | None):
        self.instance = instance
        self.solution = list(solution) if solution is not None else None
        self.redraw()

    # ── dispatch ─────────────────────────────────────────────────────────────
    def redraw(self):
        self.delete("all")
        w = max(self.winfo_width(),  720)
        h = max(self.winfo_height(), 420)

        if self._mode == "2d":
            self._draw_2d(w, h)
        else:
            self._draw_1d(w, h)

        self._draw_toggle(w, h)

    # ════════════════════  1D — GIỮ NGUYÊN BẢN GỐC  ═════════════════════════
    def _draw_1d(self, w, h):
        truck_x, truck_y = 30, 90
        truck_w = int(w * 0.72)
        truck_h = int(h * 0.48)
        cabin_w = int(truck_w * 0.16)

        # Thân xe
        self.create_rectangle(
            truck_x, truck_y, truck_x + truck_w, truck_y + truck_h,
            outline="#2e3440", width=2, fill="#eef2f7")
        # Cabin
        self.create_rectangle(
            truck_x + truck_w, truck_y + 35,
            truck_x + truck_w + cabin_w, truck_y + truck_h,
            outline="#2e3440", width=2, fill="#d8dee9")
        # Bánh
        self.create_oval(truck_x + 80, truck_y + truck_h - 10,
                          truck_x + 130, truck_y + truck_h + 40, fill="#2e3440")
        self.create_oval(truck_x + truck_w - 40, truck_y + truck_h - 10,
                          truck_x + truck_w + 10, truck_y + truck_h + 40, fill="#2e3440")
        self.create_oval(truck_x + truck_w + cabin_w - 50, truck_y + truck_h - 10,
                          truck_x + truck_w + cabin_w, truck_y + truck_h + 40, fill="#2e3440")
        self.create_text(truck_x + 10, truck_y - 20, anchor="w",
                         text="Mô phỏng xếp hàng vào xe tải",
                         font=("Segoe UI", 11, "bold"))

        if not self.instance or not self.solution:
            self.create_text(w // 2, h // 2,
                             text="Chưa có nghiệm để mô phỏng",
                             fill="#666666", font=("Segoe UI", 12, "italic"))
            return

        selected_indices   = [i for i, g in enumerate(self.solution) if g == 1]
        unselected_indices = [i for i, g in enumerate(self.solution) if g == 0]

        self.create_text(
            truck_x + 10, truck_y + 10, anchor="nw",
            text=f"Chọn {len(selected_indices)} / {len(self.solution)} kiện hàng",
            font=("Segoe UI", 10, "bold"), fill="#2e3440")

        inner_x = truck_x + 15
        inner_y = truck_y + 40
        inner_w = truck_w - 30
        inner_h = truck_h - 55
        x = inner_x; y = inner_y; row_height = 0

        for k, idx in enumerate(selected_indices):
            item = self.instance.items[idx]
            bw = max(36, min(90, int(28 + item.weight * 1.8)))
            bh = max(28, min(54, int(22 + math.sqrt(max(item.value, 1)))))

            if x + bw > inner_x + inner_w:
                x = inner_x; y += row_height + 8; row_height = 0
            if y + bh > inner_y + inner_h:
                break

            color = BOX_COLORS[k % len(BOX_COLORS)]
            self.create_rectangle(x, y, x + bw, y + bh,
                                   fill=color, outline="#4c566a", width=1)
            self.create_text(x + bw / 2, y + bh / 2,
                             text=f"P{item.id}\nW:{item.weight:g}",
                             font=("Segoe UI", 8))
            x += bw + 8
            row_height = max(row_height, bh)

        # Kiện không được chọn
        start_y = truck_y + truck_h + 70
        self.create_text(30, start_y - 18, anchor="w",
                         text="Kiện hàng chưa được chọn:",
                         font=("Segoe UI", 10, "bold"), fill="#4c566a")
        x = 30; y = start_y; row_height = 0

        for idx in unselected_indices[:24]:
            item = self.instance.items[idx]
            bw, bh = 58, 32
            if x + bw > w - 30:
                x = 30; y += row_height + 8; row_height = 0
            self.create_rectangle(x, y, x + bw, y + bh,
                                   fill="#f1f3f5", outline="#adb5bd")
            self.create_text(x + bw / 2, y + bh / 2,
                             text=f"P{item.id}",
                             font=("Segoe UI", 8), fill="#495057")
            x += bw + 6
            row_height = max(row_height, bh)

    # ════════════════════  2D — RESIDENT EVIL INVENTORY  ════════════════════
    def _draw_2d(self, w, h):
        """
        Lưới 2D kiểu Resident Evil:
        - Capacity làm tròn lên bội 10, chia thành lưới COLS x ROWS ô.
        - Mỗi kiện được chọn chiếm 1 hình chữ nhật gồm n_cols x n_rows ô
          tính từ weight (ceil(weight/10) ô, xếp thành hình chữ nhật gần vuông).
        - Pack kiện vào lưới theo shelf-packing từ trái sang phải, trên xuống dưới.
        - Ô trống màu xám, có chấm nhỏ.
        """
        if not self.instance:
            self.create_text(w // 2, h // 2,
                             text="Chưa có dữ liệu",
                             fill="#666666", font=("Segoe UI", 12, "italic"))
            return

        PAD = 20; TITLE_H = 32

        cap_real  = self.instance.capacity
        cap_round = math.ceil(cap_real / 10) * 10   # làm tròn lên bội 10
        total_units = cap_round // 10               # tổng số đơn vị ô

        # ── Tính kích thước lưới — luôn vừa khít canvas ────────────────────
        STATS_H     = 50    # chừa stats dưới
        grid_area_w = w - PAD * 2
        grid_area_h = h - TITLE_H - PAD - STATS_H

        # Bước 1: tìm COLS cho lưới gần vuông nhất
        best_cols = max(1, min(total_units, 12))
        best_score = -1
        for cols_try in range(1, total_units + 1):
            rows_try = math.ceil(total_units / cols_try)
            # cell_size tối đa vừa cả w và h
            gap_try  = max(1, min(3, grid_area_w // (cols_try * 10)))
            cw = (grid_area_w - gap_try * (cols_try - 1)) / cols_try
            ch = (grid_area_h - gap_try * (rows_try - 1)) / rows_try
            cell_try = min(cw, ch)
            # score: ưu tiên cell lớn và tỉ lệ gần vuông (cols ≈ rows)
            ratio_score = 1.0 - abs(cols_try - rows_try) / max(cols_try + rows_try, 1)
            score = cell_try * (0.7 + 0.3 * ratio_score)
            if score > best_score:
                best_score = score
                best_cols  = cols_try

        COLS = best_cols
        ROWS = math.ceil(total_units / COLS)

        # Bước 2: tính GAP và CELL sao cho lưới KHÔNG vượt quá canvas
        GAP  = max(1, min(3, grid_area_w // (COLS * 10)))
        # CELL bị giới hạn bởi cả chiều rộng và chiều cao
        CELL = int(min(
            (grid_area_w - GAP * (COLS - 1)) / COLS,
            (grid_area_h - GAP * (ROWS - 1)) / max(ROWS, 1),
        ))
        CELL = max(12, CELL)

        # Bước 3: tính kích thước thực và căn giữa
        grid_w = COLS * (CELL + GAP) - GAP
        grid_h = ROWS * (CELL + GAP) - GAP
        grid_x = (w - grid_w) // 2
        grid_y = TITLE_H + PAD // 2

        # ── Tiêu đề ──────────────────────────────────────────────────────────
        self.create_text(
            w // 2, TITLE_H // 2, anchor="center",
            text=f"Ô Sắp Xếp ({COLS}×{ROWS})  —  {cap_real:.1f} kg  "
                 f"({'→ ' + str(cap_round) + ' kg' if cap_round != cap_real else ''})",
            font=("Segoe UI", 10, "bold"), fill=_BD)

        # ── Linear fill — đảm bảo 100% kiện được chọn đều hiện lên lưới ────
        # Mỗi kiện chiếm `units` ô liên tiếp (đọc như văn bản: trái→phải, trên→dưới).
        # Nếu block trải qua nhiều hàng thì vẽ từng đoạn hàng riêng.
        # Cách này không bao giờ "hết chỗ" vì tổng ô = total_units >= tổng weight chọn.
        cell_owner: list = [None] * total_units   # cell_owner[i] = color
        item_placements = []   # [(item, r, c, nr, nc, color)]

        if self.solution:
            selected = [(self.instance.items[i], i)
                        for i, g in enumerate(self.solution) if g == 1]

            cursor = 0
            for item, orig_i in selected:
                units = max(1, math.ceil(item.weight / _KG_CELL))
                color = BOX_COLORS[orig_i % len(BOX_COLORS)]

                start = cursor
                for _ in range(units):
                    if cursor < total_units:
                        cell_owner[cursor] = color
                        cursor += 1

                actual_units = cursor - start
                end   = start + actual_units - 1
                r_s   = start // COLS;  c_s = start % COLS
                r_e   = end   // COLS;  c_e = end   % COLS

                if r_s == r_e:
                    # Gọn trong 1 hàng
                    item_placements.append((item, r_s, c_s, 1, c_e - c_s + 1, color))
                else:
                    # Hàng đầu
                    item_placements.append((item, r_s, c_s, 1, COLS - c_s, color))
                    # Hàng giữa
                    for mid_r in range(r_s + 1, r_e):
                        item_placements.append((item, mid_r, 0, 1, COLS, color))
                    # Hàng cuối
                    item_placements.append((item, r_e, 0, 1, c_e + 1, color))

        # ── Vẽ nền lưới ──────────────────────────────────────────────────────
        # Khung ngoài
        self.create_rectangle(
            grid_x - 4, grid_y - 4,
            grid_x + grid_w + 4, grid_y + grid_h + 4,
            fill="#b8c0d8", outline="#8d94b8", width=2)

        # Vẽ ô trống — màu phụ thuộc vào trạng thái có nghiệm hay chưa
        has_sol = bool(self.solution)
        ef  = _EMPTY_HAS_SOL if has_sol else _EMPTY_NO_SOL
        ebd = _EMPTY_BD_HAS  if has_sol else _EMPTY_BD_NO
        for ci in range(total_units):
            if cell_owner[ci] is None:
                r = ci // COLS; c = ci % COLS
                x1 = grid_x + c * (CELL + GAP)
                y1 = grid_y + r * (CELL + GAP)
                x2 = x1 + CELL; y2 = y1 + CELL
                self.create_rectangle(x1, y1, x2, y2,
                                       fill=ef, outline=ebd, width=1)
                if CELL >= 16:
                    cx2 = (x1 + x2) // 2; cy2 = (y1 + y2) // 2
                    dot = max(1, CELL // 8)
                    self.create_oval(cx2-dot, cy2-dot, cx2+dot, cy2+dot,
                                      fill=ebd, outline="")

        # ── Vẽ kiện hàng ─────────────────────────────────────────────────────
        for item, r0, c0, nr, nc, color in item_placements:
            x1 = grid_x + c0 * (CELL + GAP)
            y1 = grid_y + r0 * (CELL + GAP)
            x2 = x1 + nc * (CELL + GAP) - GAP
            y2 = y1 + nr * (CELL + GAP) - GAP

            # Bo góc nhẹ bằng polygon smooth
            self._rrect(x1, y1, x2, y2, r=max(2, CELL // 5),
                        fill=color, outline=_BD, width=1)

            # Text: ID + weight
            cx = (x1 + x2) // 2; cy = (y1 + y2) // 2
            box_w = x2 - x1; box_h = y2 - y1
            if box_w >= 24 and box_h >= 18:
                fs = max(7, min(12, box_w // 5))
                self.create_text(cx, cy - (5 if box_h >= 30 else 0),
                                 text=str(item.id),
                                 font=("Segoe UI", fs, "bold"),
                                 fill=_BD)
                if box_h >= 30:
                    self.create_text(cx, cy + fs,
                                     text=f"{item.weight:g}kg",
                                     font=("Segoe UI", max(6, fs - 2)),
                                     fill=_BD)

        # ── Stats dưới ───────────────────────────────────────────────────────
        sy = grid_y + grid_h + 12
        if self.solution:
            sel   = [self.instance.items[i]
                     for i, g in enumerate(self.solution) if g == 1]
            tw    = sum(it.weight for it in sel)
            tv    = sum(it.value  for it in sel)
            pct   = tw / cap_real * 100 if cap_real > 0 else 0
            placed = len(selected)  # linear fill luôn xếp đủ
            stats = [
                ("Tải trọng", f"{tw:.1f}/{cap_real:.1f} kg"),
                ("Fill",      f"{pct:.1f}%"),
                ("Giá trị",   f"{tv:.1f}"),
                ("Xếp được",  f"{placed}/{len(sel)} kiện"),
            ]
        else:
            stats = [("Capacity", f"{cap_real:.1f} kg → {total_units} ô")]

        if sy + 30 < h:
            # Nền trắng che phủ phần lưới có thể tràn xuống
            self.create_rectangle(0, sy - 6, w, h,
                                   fill="white", outline="")
            # Đường kẻ phân cách nhẹ
            self.create_line(PAD, sy - 4, w - PAD, sy - 4,
                              fill="#dde3f2", width=1)
            sw = max(1, (w - PAD * 2) // max(len(stats), 1))
            for i, (lbl, val) in enumerate(stats):
                cx = PAD + sw * i + sw // 2
                self.create_text(cx, sy,
                                 text=lbl, font=("Segoe UI", 7),
                                 fill="#8890b0", anchor="center")
                self.create_text(cx, sy + 14,
                                 text=val,
                                 font=("Segoe UI", 9, "bold"),
                                 fill=_BD, anchor="center")

    # ════════════════════  NÚT TOGGLE (tròn, góc trên trái)  ════════════════
    def _draw_toggle(self, w, h):
        R  = 16
        cx = R + 10   # góc trên TRÁI
        cy = R + 10

        # Shadow
        self.create_oval(cx - R + 1, cy - R + 1,
                          cx + R + 2, cy + R + 2,
                          fill="#c0c8e0", outline="", tags="tgl")

        # Circle
        bg = _TOGGLE_C if self._mode == "2d" else "#ffffff"
        fg = "#ffffff"  if self._mode == "2d" else _TOGGLE_C
        self.create_oval(cx - R, cy - R, cx + R, cy + R,
                          fill=bg, outline=_TOGGLE_C, width=2, tags="tgl")

        # Label: hiện chế độ ĐANG HIỂN THỊ
        label = "1D" if self._mode == "1d" else "2D"
        self.create_text(cx, cy, text=label,
                          font=("Segoe UI", 8, "bold"),
                          fill=fg, tags="tgl")

        for tag in ("tgl",):
            self.tag_bind(tag, "<Button-1>", self._on_toggle)
            self.tag_bind(tag, "<Enter>",
                           lambda e: self.config(cursor="hand2"))
            self.tag_bind(tag, "<Leave>",
                           lambda e: self.config(cursor=""))

    def _on_toggle(self, event=None):
        self._mode = "2d" if self._mode == "1d" else "1d"
        self.redraw()

    # ── helper bo góc ────────────────────────────────────────────────────────
    def _rrect(self, x1, y1, x2, y2, r=6, **kw):
        r = min(r, (x2 - x1) // 2, (y2 - y1) // 2)
        pts = [
            x1 + r, y1,     x2 - r, y1,
            x2,     y1,     x2,     y1 + r,
            x2,     y2 - r, x2,     y2,
            x2 - r, y2,     x1 + r, y2,
            x1,     y2,     x1,     y2 - r,
            x1,     y1 + r, x1,     y1,
            x1 + r, y1,
        ]
        self.create_polygon(pts, smooth=True, **kw)