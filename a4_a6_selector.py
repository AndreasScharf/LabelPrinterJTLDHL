# a4_a6_selector.py
import tkinter as tk
from tkinter import ttk

A4_W, A4_H = 210, 297  # DIN A sizes in mm, only for aspect ratio

class A4A6Selector(ttk.Frame):
    """
    A4 aspect canvas subdivided into four A6 cells (2x2).
    Click a cell to toggle selection. Exposes .get_selected() -> set of ids.
    """
    def __init__(self, master, cell_names=("TL", "TR", "BL", "BR"), **kw):
        super().__init__(master, **kw)

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # selection state per cell-id: {0..3: bool}
        self.state = {i: False for i in range(4)}
        self.cell_names = cell_names

        # ids for canvas items
        self._outer_rect = None
        self._cell_rects = {}  # i -> rect_id
        self._cell_tags = {}   # i -> tag string

        # colors
        self.bg = self.winfo_toplevel().cget("bg")
        self.stroke = "#4a4a4a"
        self.sel_fill = "#7db3ff"   # selected fill (light, visible on dark/light)
        self.sel_alpha = 0.35       # simulated alpha via stipple
        self.grid_stroke = "#8b8b8b"

        self.canvas.bind("<Configure>", self._redraw)
        self.canvas.bind("<Button-1>", self._on_click)

        # status line (optional)
        self.status = tk.StringVar(value="Selected: none")
        ttk.Label(self, textvariable=self.status, anchor="w").pack(fill="x", padx=2, pady=(4, 0))

    # ----- public API
    def get_selected(self):
        """Return a set of selected cell indices {0..3}."""


        return [i for i, v in self.state.items() if v]

    def set_selected(self, indices):
        """Programmatically set selected cells."""
        self.state = {i: (i in indices) for i in range(4)}
        self._paint_selection()
        self._update_status()

    # ----- drawing
    def _redraw(self, event=None):
        self.canvas.delete("all")
        self._cell_rects.clear()
        self._cell_tags.clear()

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        # compute A4 area fitting inside current canvas while keeping aspect
        target_aspect = A4_W / A4_H
        canvas_aspect = w / h if h else target_aspect
        if canvas_aspect > target_aspect:
            # canvas wider: limit by height
            a4_h = h * 0.92
            a4_w = a4_h * target_aspect
        else:
            # canvas taller: limit by width
            a4_w = w * 0.92
            a4_h = a4_w / target_aspect

        # center A4 rect
        x0 = (w - a4_w) / 2
        y0 = (h - a4_h) / 2
        x1 = x0 + a4_w
        y1 = y0 + a4_h

        # outer A4
        self._outer_rect = self.canvas.create_rectangle(
            x0, y0, x1, y1, outline=self.stroke, width=2, fill=""
        )

        # split into 2x2 A6
        mx = (x0 + x1) / 2
        my = (y0 + y1) / 2

        # grid lines
        self.canvas.create_line(mx, y0, mx, y1, fill=self.grid_stroke, width=1)
        self.canvas.create_line(x0, my, x1, my, fill=self.grid_stroke, width=1)

        # cells (TL, TR, BL, BR) -> indices 0..3
        cells = [
            (x0, y0, mx, my),  # 0 TL
            (mx, y0, x1, my),  # 1 TR
            (x0, my, mx, y1),  # 2 BL
            (mx, my, x1, y1),  # 3 BR
        ]

        for i, (cx0, cy0, cx1, cy1) in enumerate(cells):
            tag = f"cell{i}"
            self._cell_tags[i] = tag

            # invisible rect to receive clicks; we draw fills/overlays separately
            r = self.canvas.create_rectangle(
                cx0, cy0, cx1, cy1,
                tags=(tag, "cell"),
                outline="", fill=""
            )
            self._cell_rects[i] = r

            # label each cell
            label = self.cell_names[i] if i < len(self.cell_names) else str(i)
            self.canvas.create_text(
                (cx0 + cx1) / 2, (cy0 + cy1) / 2,
                text=f"A6 {label}", font=("Segoe UI", 11, "bold"),
            )

        # paint selection overlays on top
        self._paint_selection()
        self._update_status()

    def _paint_selection(self):
        # remove old overlays
        self.canvas.delete("sel_overlay")

        for i, rect_id in self._cell_rects.items():
            if self.state[i]:
                # get current coords of the cell rect
                x0, y0, x1, y1 = self.canvas.coords(rect_id)
                # draw a semi-opaque overlay (simulate alpha via stipple)
                self.canvas.create_rectangle(
                    x0, y0, x1, y1,
                    fill=self.sel_fill,
                    stipple="gray50",  # fake 50% transparency
                    outline="",
                    tags=("sel_overlay",),
                )
                # add a stronger border for selected
                self.canvas.create_rectangle(
                    x0, y0, x1, y1,
                    outline=self.sel_fill,
                    width=2,
                    dash=(),
                    tags=("sel_overlay",),
                )

    # ----- interactions
    def _which_cell(self, x, y):
        """Return cell index at (x,y) or None."""
        items = self.canvas.find_overlapping(x, y, x, y)
        for item in items:
            tags = self.canvas.gettags(item)
            for i, tag in self._cell_tags.items():
                if tag in tags:
                    return i
        return None

    def _on_click(self, event):
        cid = self._which_cell(event.x, event.y)
        if cid is None:
            return
        # toggle
        self.state[cid] = not self.state[cid]
        self._paint_selection()
        self._update_status()

    def _update_status(self):
        names = [self.cell_names[i] if i < len(self.cell_names) else str(i)
                 for i in self.get_selected()]
        self.status.set("Selected: " + (", ".join(names) if names else "none"))

