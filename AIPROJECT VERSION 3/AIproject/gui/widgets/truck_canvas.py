from __future__ import annotations

import math
import tkinter as tk
from typing import Iterable, List

from core.models import KnapsackInstance


BOX_COLORS = [
    "#88c0d0", "#a3be8c", "#ebcb8b", "#d08770", "#b48ead",
    "#5e81ac", "#8fbcbb", "#bf616a", "#81a1c1", "#d8dee9"
]


class TruckCanvas(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg="white", highlightthickness=1, highlightbackground="#cccccc", **kwargs)
        self.instance: KnapsackInstance | None = None
        self.solution: List[int] | None = None
        self.bind("<Configure>", lambda e: self.redraw())

    def set_solution(self, instance: KnapsackInstance, solution: Iterable[int] | None):
        self.instance = instance
        self.solution = list(solution) if solution is not None else None
        self.redraw()

    def redraw(self):
        self.delete("all")
        w = max(self.winfo_width(), 720)
        h = max(self.winfo_height(), 420)

        truck_x, truck_y = 30, 90
        truck_w, truck_h = int(w * 0.72), int(h * 0.48)
        cabin_w = int(truck_w * 0.16)

        self.create_rectangle(truck_x, truck_y, truck_x + truck_w, truck_y + truck_h, outline="#2e3440", width=2, fill="#eef2f7")
        self.create_rectangle(truck_x + truck_w, truck_y + 35, truck_x + truck_w + cabin_w, truck_y + truck_h, outline="#2e3440", width=2, fill="#d8dee9")
        self.create_oval(truck_x + 80, truck_y + truck_h - 10, truck_x + 130, truck_y + truck_h + 40, fill="#2e3440")
        self.create_oval(truck_x + truck_w - 40, truck_y + truck_h - 10, truck_x + truck_w + 10, truck_y + truck_h + 40, fill="#2e3440")
        self.create_oval(truck_x + truck_w + cabin_w - 50, truck_y + truck_h - 10, truck_x + truck_w + cabin_w, truck_y + truck_h + 40, fill="#2e3440")
        self.create_text(truck_x + 10, truck_y - 20, anchor="w", text="Mô phỏng xếp hàng vào xe tải", font=("Segoe UI", 11, "bold"))

        if not self.instance or not self.solution:
            self.create_text(w // 2, h // 2, text="Chưa có nghiệm để mô phỏng", fill="#666666", font=("Segoe UI", 12, "italic"))
            return

        selected_indices = [i for i, g in enumerate(self.solution) if g == 1]
        unselected_indices = [i for i, g in enumerate(self.solution) if g == 0]

        self.create_text(
            truck_x + 10,
            truck_y + 10,
            anchor="nw",
            text=f"Chọn {len(selected_indices)} / {len(self.solution)} kiện hàng",
            font=("Segoe UI", 10, "bold"),
            fill="#2e3440"
        )

        inner_x = truck_x + 15
        inner_y = truck_y + 40
        inner_w = truck_w - 30
        inner_h = truck_h - 55

        x = inner_x
        y = inner_y
        row_height = 0

        for k, idx in enumerate(selected_indices):
            item = self.instance.items[idx]
            bw = max(36, min(90, int(28 + item.weight * 1.8)))
            bh = max(28, min(54, int(22 + math.sqrt(max(item.value, 1)))))

            if x + bw > inner_x + inner_w:
                x = inner_x
                y += row_height + 8
                row_height = 0

            if y + bh > inner_y + inner_h:
                break

            color = BOX_COLORS[k % len(BOX_COLORS)]
            self.create_rectangle(x, y, x + bw, y + bh, fill=color, outline="#4c566a", width=1)
            self.create_text(x + bw / 2, y + bh / 2, text=f"P{item.id}\nW:{item.weight:g}", font=("Segoe UI", 8))
            x += bw + 8
            row_height = max(row_height, bh)

        start_y = truck_y + truck_h + 70
        self.create_text(
            30,
            start_y - 18,
            anchor="w",
            text="Kiện hàng chưa được chọn:",
            font=("Segoe UI", 10, "bold"),
            fill="#4c566a"
        )

        x = 30
        y = start_y
        row_height = 0

        for idx in unselected_indices[:24]:
            item = self.instance.items[idx]
            bw, bh = 58, 32

            if x + bw > w - 30:
                x = 30
                y += row_height + 8
                row_height = 0

            self.create_rectangle(x, y, x + bw, y + bh, fill="#f1f3f5", outline="#adb5bd")
            self.create_text(x + bw / 2, y + bh / 2, text=f"P{item.id}", font=("Segoe UI", 8), fill="#495057")
            x += bw + 6
            row_height = max(row_height, bh)