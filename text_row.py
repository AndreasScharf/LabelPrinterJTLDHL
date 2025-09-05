import os
import hashlib
import datetime as _dt
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont


class StatusKnob(ttk.Frame):
    """Small colored circle: set(True) -> green, set(False) -> red, set(None) -> gray."""
    def __init__(self, master, size=12, **kw):
        super().__init__(master, **kw)
        self.size = size
        self.canvas = tk.Canvas(self, width=size, height=size,
                                highlightthickness=0, bg=self._bg())
        self.canvas.pack()
        self._dot = self.canvas.create_oval(1, 1, size-1, size-1,
                                            outline="", fill="#aaa")

    def _bg(self):
        try:
            return ttk.Style().lookup("TFrame", "background") or self.master.cget("background")
        except Exception:
            return self.master.cget("background")

    def set(self, state: bool | None):
        color = "#4CAF50" if state is True else ("#E53935" if state is False else "#AAAAAA")
        self.canvas.itemconfigure(self._dot, fill=color)


class TextRow(ttk.Frame):
    """
    A labeled multi-line text editor with footer:
      - Internetmarke combobox (vertical)
      - 'gekauft' status knob (auto-updates on text change)
    """
    def __init__(self, master, title="Section", **kw):
        super().__init__(master, **kw)
        self._purchase_dir = "purchases"  # folder where <hash>.pdf is expected

        # ---- Header ----
      
        # ---- Header ----
        header = ttk.Frame(self)
        header.pack(fill="x", padx=0, pady=(0, 4))

        self.title_var = tk.StringVar(value=title)

        # Bold + larger font for title
        bold_font = tkfont.nametofont("TkDefaultFont").copy()
        bold_font.configure(weight="bold", size=bold_font.cget("size") + 1)

        ttk.Label(header, textvariable=self.title_var, font=bold_font).pack(
            side="left", anchor="w"
        )

        # Separator line below header
        sep = ttk.Separator(self, orient="horizontal")
        sep.pack(fill="x", pady=(0, 4))

        # ---- Text area (Anschrift) ----
        self.text = tk.Text(self, wrap="word", height=6)
        self.text.pack(fill="both", expand=True)
        self.text.bind("<<Modified>>", self._on_text_change)

        # ---- Footer (two rows) ----
        footer = ttk.Frame(self)
        footer.pack(fill="x", pady=(6, 0))

        # Row 1: Internetmarke label + combobox
        row1 = ttk.Frame(footer)
        row1.pack(fill="x", pady=(0, 4))

        ttk.Label(row1, text="Internetmarke:").pack(side="left", padx=(0, 6))
        self._marke_var = tk.StringVar(value="-")
        self._marke_cb = ttk.Combobox(
            row1,
            textvariable=self._marke_var,
            state="readonly",
            width=24,
            values=["-"],
        )
        self._marke_cb.pack(side="left")

        # Row 2: gekauft label + knob
        row2 = ttk.Frame(footer)
        row2.pack(fill="x")

        ttk.Label(row2, text="gekauft").pack(side="left", padx=(0, 6))
        self._gekauft_knob = StatusKnob(row2, size=12)
        self._gekauft_knob.pack(side="left")

        # cache of combobox options
        self._marke_options: list[str] = ["-"]

    # ---------- Address text ----------
    def set_text(self, value: str):
        self.text.delete("1.0", "end")
        if value:
            self.text.insert("1.0", value)
        self._on_text_change()

    def get_text(self) -> str:
        return self.text.get("1.0", "end-1c")

   # ---------- Internetmarke ----------
    def set_internetmarke_options(self, options: list[tuple[str, str]]):
        """
        options: list of (value, text) tuples.
        The combobox will show 'text' but you can get/set using 'value'.
        """
        clean = [("-", "-")] + [opt for opt in options if opt[0] and opt[1]]
        self._marke_options = clean  # store full tuples

        # mapping for quick lookup
        self._marke_text_to_val = {text: val for val, text in clean}
        self._marke_val_to_text = {val: text for val, text in clean}

        # put only the text into the combobox
        texts = [text for _, text in clean]
        current_val = self.get_internetmarke()  # current value

        self._marke_cb["values"] = texts
        if current_val in self._marke_val_to_text:
            self._marke_var.set(self._marke_val_to_text[current_val])
        else:
            self._marke_var.set("-")

    def get_internetmarke(self) -> str | None:
        """Return the selected 'value' or None if '-'."""
        text = self._marke_var.get()
        val = self._marke_text_to_val.get(text)
        return None if val == "-" else val

    def set_internetmarke(self, value: str | None):
        """Programmatically select by 'value'."""
        if not value or value == "-":
            self._marke_var.set("-")
            return
        text = self._marke_val_to_text.get(value)
        if text:
            self._marke_var.set(text)
        else:
            # unknown → add it temporarily
            self._marke_options.append((value, value))
            self._marke_val_to_text[value] = value
            self._marke_text_to_val[value] = value
            self._marke_cb["values"] = [t for _, t in self._marke_options]
            self._marke_var.set(value)

    def get_internetmarke_index(self) -> int | None:
        """
        Return the selected index in the combobox values list.
        Returns None if nothing is selected or if '-' is selected.
        """
        idx = self._marke_cb.current()
        if idx is None or idx < 0:
            return None
        # if first entry is "-" then treat it as None
        if self._marke_cb["values"][idx] == "-":
            return None
        return idx
    
    def auto_select_internetmarke_for_country(self, country_code: str):
        if not country_code:
            return
        cc = country_code.strip().upper()
        if cc in ("DE", "DEU", "GERMANY", "DEUTSCHLAND"):
            self._marke_var.set(self._marke_options[1][1])


    # ---------- gekauft status ----------
    def set_purchase_dir(self, path: str):
        self._purchase_dir = path

    def compute_purchase_hash(self, date_iso: str | None = None) -> str:
        if not date_iso:
            date_iso = _dt.date.today().isoformat()
        key = (self.get_text().strip() + "\n" + date_iso).encode("utf-8")
        return hashlib.md5(key).hexdigest()

    def expected_purchase_path(self, ext: str = ".pdf", date_iso: str | None = None) -> str:
        h = self.compute_purchase_hash(date_iso=date_iso)
        return os.path.join(self._purchase_dir, f"{h}{ext}")

    def check_purchase_status(self, date_iso: str | None = None) -> bool | None:
        path = self.expected_purchase_path(date_iso=date_iso)
        exists = os.path.exists(path)
        self._gekauft_knob.set(True if exists else None)
        return True if exists else None

    # ---------- event handlers ----------
    def _on_text_change(self, event=None):
        if event:
            # reset modified flag
            self.text.edit_modified(False)
        self.check_purchase_status()
