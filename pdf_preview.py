# pdf_preview.py (or inside your app file)
import io
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import fitz  # PyMuPDF

class PDFPreview(ttk.Frame):
    def __init__(self, master, pdf_blob: bytes = None, pdf_path: str = None, **kw):
        super().__init__(master, **kw)

        if not (pdf_blob or pdf_path):
            raise ValueError("Provide either pdf_blob or pdf_path")

        # --- load document from blob or path
        if pdf_blob:
            self.doc = fitz.open(stream=pdf_blob, filetype="pdf")
        else:
            self.doc = fitz.open(pdf_path)

        self.cur_page = 0
        self.zoom = 1.0

        # --- UI
        # toolbar
        tb = ttk.Frame(self)
        tb.pack(fill="x", pady=(0, 6))
        self.prev_btn = ttk.Button(tb, text="◀", width=3, command=self.prev_page)
        self.prev_btn.pack(side="left")
        self.next_btn = ttk.Button(tb, text="▶", width=3, command=self.next_page)
        self.next_btn.pack(side="left", padx=(4, 8))

        ttk.Label(tb, text="Zoom").pack(side="left")
        self.zoom_var = tk.DoubleVar(value=100.0)
        self.zoom_scale = ttk.Scale(tb, from_=50, to=200, variable=self.zoom_var,
                                    command=self._on_zoom_change)
        self.zoom_scale.pack(side="left", fill="x", expand=True, padx=8)
        self.page_label = ttk.Label(tb, text="")
        self.page_label.pack(side="right")

        # scrollable canvas for page
        wrap = ttk.Frame(self)
        wrap.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(wrap, background="#f1f2f4", highlightthickness=0)
        self.vbar = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.hbar = ttk.Scrollbar(wrap, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.vbar.set, xscrollcommand=self.hbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.hbar.grid(row=1, column=0, sticky="ew")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        # container item inside canvas to place the image nicely centered
        self.page_container = self.canvas.create_rectangle(0, 0, 0, 0, outline="")

        # track resize to keep page centered
        self.canvas.bind("<Configure>", lambda e: self._render_page())

        # store image refs
        self._img_tk = None

        self._render_page()

    # --- controls
    def _on_zoom_change(self, _evt=None):
        self.zoom = self.zoom_var.get() / 100.0
        self._render_page()

    def prev_page(self):
        if self.cur_page > 0:
            self.cur_page -= 1
            self._render_page()

    def next_page(self):
        if self.cur_page < len(self.doc) - 1:
            self.cur_page += 1
            self._render_page()

    # --- rendering
    def _render_page(self):
        page = self.doc[self.cur_page]

        # Fitz: matrix for zoom; 72 dpi base → scale by zoom
        mat = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)  # RGB

        # PIL image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # add a white page with margin + soft shadow to mimic A4
        margin = 16  # px white border around the page
        shadow = 10  # px shadow blur margin
        canvas_w = img.width + 2 * margin + shadow
        canvas_h = img.height + 2 * margin + shadow
        viz = Image.new("RGB", (canvas_w, canvas_h), "#f1f2f4")

        # simple soft shadow rectangle
        shadow_img = Image.new("RGBA", (img.width + 20, img.height + 20), (0, 0, 0, 0))
        # draw a faint shadow by pasting a semi-transparent gray rect
        sbox = Image.new("RGBA", (img.width, img.height), (0, 0, 0, 30))
        shadow_img.paste(sbox, (10, 10))
        viz.paste(shadow_img, (margin - 10, margin - 10), shadow_img)

        # paste white page background
        page_bg = Image.new("RGB", (img.width, img.height), "white")
        viz.paste(page_bg, (margin, margin))
        # paste the PDF bitmap on top
        viz.paste(img, (margin, margin))

        # to Tk
        self._img_tk = ImageTk.PhotoImage(viz)

        # center inside canvas
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        x = max((cw - viz.width) // 2, 0)
        y = max((ch - viz.height) // 2, 0)

        # clear and draw
        self.canvas.delete("pageimg")
        self.canvas.create_image(x, y, anchor="nw", image=self._img_tk, tags="pageimg")

        # update scroll region
        self.canvas.config(scrollregion=(0, 0, max(viz.width, cw), max(viz.height, ch)))

        # update page label
        self.page_label.config(text=f"Seite {self.cur_page + 1} / {len(self.doc)}")

def show_pdf_preview_toplevel(root, pdf_blob: bytes = None, pdf_path: str = None, title="Vorschau"):
    win = tk.Toplevel(root)
    win.title(title)
    win.geometry("900x700")
    win.minsize(640, 480)

   

    viewer = PDFPreview(win, pdf_blob=pdf_blob, pdf_path=pdf_path)
    viewer.pack(fill="both", expand=True)
    win.transient(root)  # keep on top of parent in task switchers
    win.grab_set()       # modal-ish; comment out if not desired
    return viewer, win
