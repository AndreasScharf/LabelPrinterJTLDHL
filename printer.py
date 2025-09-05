# --- cross-platform printer utilities and enhanced preview+print window ---

import os
import sys
import time
import tempfile
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional

from pdf_preview import PDFPreview

# ---------- Printer discovery ----------
def list_printers_unix() -> List[str]:
    try:
        out = subprocess.check_output(["lpstat", "-a"], stderr=subprocess.STDOUT).decode()
        return [line.split()[0] for line in out.splitlines() if line.strip()]
    except Exception:
        return []

def list_printers_windows() -> List[str]:
    try:
        import win32print
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        return [p[2] for p in win32print.EnumPrinters(flags)]
    except Exception:
        # Fallback to default only if available
        try:
            import win32print
            return [win32print.GetDefaultPrinter()]
        except Exception:
            return []

def list_printers() -> List[str]:
    if sys.platform == "darwin" or sys.platform.startswith("linux"):
        return list_printers_unix()
    elif os.name == "nt":
        return list_printers_windows()
    else:
        return []

# ---------- Printing backends ----------
class PrintError(Exception): pass

def _cups_build_options(
    grayscale: bool,
    duplex_mode: str,        # "none" | "long" | "short"
    media: str,              # "A4" | "Letter"
    orientation: str,        # "portrait" | "landscape"
) -> List[str]:
    opts = []
    if grayscale:
        # Common across many drivers
        opts += ["-o", "ColorModel=Gray"]
    if duplex_mode == "long":
        opts += ["-o", "sides=two-sided-long-edge"]
    elif duplex_mode == "short":
        opts += ["-o", "sides=two-sided-short-edge"]
    # media (paper size)
    if media.upper() in ("A4", "LETTER"):
        opts += ["-o", f"media={media.upper()}"]
    # orientation-requested: 3=portrait, 4=landscape (CUPS IPP)
    if orientation == "landscape":
        opts += ["-o", "orientation-requested=4"]
    else:
        opts += ["-o", "orientation-requested=3"]
    return opts

def _print_macos_linux(
    pdf_bytes: bytes,
    printer: Optional[str],
    copies: int,
    pages: Optional[str],
    grayscale: bool,
    duplex_mode: str,
    media: str,
    orientation: str,
):
    cmd = ["lp"]
    if printer:
        cmd += ["-d", printer]
    if copies and copies > 1:
        cmd += ["-n", str(copies)]
    if pages:
        # CUPS accepts -P "1-3,5"
        cmd += ["-P", pages]
    cmd += _cups_build_options(grayscale, duplex_mode, media, orientation)
    proc = subprocess.run(cmd, input=pdf_bytes, check=False)
    if proc.returncode != 0:
        raise PrintError(f"lp failed with exit code {proc.returncode}")

def _print_windows(
    pdf_bytes: bytes,
    printer: Optional[str],
    copies: int,             # Note: ShellExecute usually ignores copies
    pages: Optional[str],    # Not supported via ShellExecute
    grayscale: bool,         # Relies on printer defaults
    duplex_mode: str,        # Relies on printer defaults
    media: str,              # Relies on printer defaults
    orientation: str,        # Relies on printer defaults
):
    """
    Windows ShellExecute requires a file path and uses the default PDF handler (Edge, Adobe, etc.).
    Per-job options (copies, duplex, grayscale) generally follow the printer/app defaults.
    If you need strict control, consider a dedicated tool or win32 GDI rendering.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    try:
        tmp.write(pdf_bytes)
        tmp.close()
        try:
            import win32api
            verb = "printto" if printer else "print"
            # For 'printto', pass printer name as parameter.
            params = f'"{tmp.name}"'
            if verb == "printto" and printer:
                params += f' "{printer}"'
            rc = win32api.ShellExecute(0, verb, tmp.name, params if verb == "printto" else None, ".", 1)
            if rc <= 32:
                raise PrintError(f"ShellExecute failed with code {rc}")
            # Give the handler time to pick up file before deletion
            time.sleep(5)
        except ImportError:
            # Fallback via PowerShell (default printer only)
            ps_cmd = ["powershell", "-NoProfile", "-Command", f"Start-Process -FilePath '{tmp.name}' -Verb Print"]
            proc = subprocess.run(ps_cmd, check=False)
            if proc.returncode != 0:
                raise PrintError(f"PowerShell print failed with code {proc.returncode}")
            time.sleep(5)
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass

def print_pdf_with_options(
    pdf_bytes: bytes,
    printer: Optional[str],
    copies: int = 1,
    pages: Optional[str] = None,
    grayscale: bool = False,
    duplex_mode: str = "none",      # "none" | "long" | "short"
    media: str = "A4",              # "A4" | "Letter"
    orientation: str = "portrait",  # "portrait" | "landscape"
):
    if not isinstance(pdf_bytes, (bytes, bytearray)):
        raise TypeError("pdf_bytes must be bytes")
    if sys.platform == "darwin" or sys.platform.startswith("linux"):
        _print_macos_linux(pdf_bytes, printer, copies, pages, grayscale, duplex_mode, media, orientation)
    elif os.name == "nt":
        _print_windows(pdf_bytes, printer, copies, pages, grayscale, duplex_mode, media, orientation)
    else:
        raise PrintError(f"Unsupported platform: {sys.platform}")

# ---------- Preview helper ----------
def preview_pdf(pdf_bytes: bytes):
    """
    Open the PDF in the system viewer (always needs a temp file).
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(pdf_bytes)
    tmp.close()
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", tmp.name])
        elif sys.platform.startswith("linux"):
            subprocess.Popen(["xdg-open", tmp.name])
        elif os.name == "nt":
            os.startfile(tmp.name)  # type: ignore[attr-defined]
        else:
            raise RuntimeError("Unsupported platform")
    except Exception as e:
        messagebox.showerror("Vorschau-Fehler", f"Preview konnte nicht geöffnet werden:\n{e}")

# ---------- Enhanced Toplevel with settings sidebar ----------
def show_pdf_preview_toplevel(root, pdf_blob: bytes = None, pdf_path: str = None, title="Vorschau"):
    win = tk.Toplevel(root)
    win.title(title)
    win.geometry("1000x720")
    win.minsize(800, 520)

    # Grid: left settings column (0), right preview column (1)
    win.columnconfigure(0, weight=0)
    win.columnconfigure(1, weight=1)
    win.rowconfigure(0, weight=1)

    # --- Left: Settings panel
    side = ttk.Frame(win, padding=12)
    side.grid(row=0, column=0, sticky="nsw")
    side.columnconfigure(0, weight=1)

    ttk.Label(side, text="Druckeinstellungen", font=("", 11, "bold")).grid(row=0, column=0, sticky="w", pady=(0,8))

    # Printer
    ttk.Label(side, text="Drucker").grid(row=1, column=0, sticky="w")
    printers = list_printers()
    printer_var = tk.StringVar(value=(printers[0] if printers else ""))
    printer_cb = ttk.Combobox(side, textvariable=printer_var, values=printers, width=28, state="readonly" if printers else "normal")
    printer_cb.grid(row=2, column=0, sticky="ew", pady=(2,8))

    # Color mode
    ttk.Label(side, text="Farbe").grid(row=3, column=0, sticky="w")
    color_var = tk.StringVar(value="farbe")  # "farbe" | "sw"
    color_row = ttk.Frame(side); color_row.grid(row=4, column=0, sticky="w", pady=(2,8))
    ttk.Radiobutton(color_row, text="Farbe", value="farbe", variable=color_var).pack(side="left", padx=(0,8))
    ttk.Radiobutton(color_row, text="Schwarzweiß", value="sw", variable=color_var).pack(side="left")

    # Copies
    ttk.Label(side, text="Exemplare").grid(row=5, column=0, sticky="w")
    copies_var = tk.IntVar(value=1)
    ttk.Spinbox(side, from_=1, to=100, textvariable=copies_var, width=6).grid(row=6, column=0, sticky="w", pady=(2,8))

    # Page range
    ttk.Label(side, text="Seiten (z. B. 1-3,5)").grid(row=7, column=0, sticky="w")
    pages_var = tk.StringVar(value="")
    ttk.Entry(side, textvariable=pages_var).grid(row=8, column=0, sticky="ew", pady=(2,8))

    # Orientation
    ttk.Label(side, text="Ausrichtung").grid(row=9, column=0, sticky="w")
    orient_var = tk.StringVar(value="portrait")  # "portrait" | "landscape"
    orient_row = ttk.Frame(side); orient_row.grid(row=10, column=0, sticky="w", pady=(2,8))
    ttk.Radiobutton(orient_row, text="Hochformat", value="portrait", variable=orient_var).pack(side="left", padx=(0,8))
    ttk.Radiobutton(orient_row, text="Querformat", value="landscape", variable=orient_var).pack(side="left")

    # Duplex
    ttk.Label(side, text="Duplex").grid(row=11, column=0, sticky="w")
    duplex_var = tk.StringVar(value="none")  # "none" | "long" | "short"
    duplex_cb = ttk.Combobox(side, textvariable=duplex_var, values=["none", "long", "short"], state="readonly", width=12)
    duplex_cb.grid(row=12, column=0, sticky="w", pady=(2,8))
    ttk.Label(side, text="(none=einseitig, long=lange Kante, short=kurze Kante)", foreground="#666").grid(row=13, column=0, sticky="w", pady=(0,8))

    # Media (paper)
    ttk.Label(side, text="Papier").grid(row=14, column=0, sticky="w")
    media_var = tk.StringVar(value="A4")  # "A4" | "Letter"
    media_cb = ttk.Combobox(side, textvariable=media_var, values=["A4", "Letter"], state="readonly", width=12)
    media_cb.grid(row=15, column=0, sticky="w", pady=(2,12))

    # Action buttons
    btns = ttk.Frame(side)
    btns.grid(row=16, column=0, sticky="ew")
    btns.columnconfigure(0, weight=1)
    ttk.Button(btns, text="Vorschau", command=lambda: _do_preview()).grid(row=0, column=0, sticky="ew", pady=(0,6))
    ttk.Button(btns, text="Drucken", command=lambda: _do_print()).grid(row=1, column=0, sticky="ew", pady=(0,6))
    ttk.Button(btns, text="Schließen", command=win.destroy).grid(row=2, column=0, sticky="ew")

    # Info line (Windows caveat)
    ttk.Label(
        side,
        text=("Hinweis: Unter Windows hängen Monochrom/Duplex/Exemplare oft von den\n"
              "Druckerstandard-Einstellungen ab."),
        foreground="#666",
        justify="left"
    ).grid(row=17, column=0, sticky="w", pady=(12,0))

    # --- Right: PDF viewer
    viewer = PDFPreview(win, pdf_blob=pdf_blob, pdf_path=pdf_path)
    viewer.grid(row=0, column=1, sticky="nsew", padx=(6,0))
    win.transient(root)
    win.grab_set()

    # --- Actions
    def _collect_options():
        return {
            "printer": (printer_var.get().strip() or None),
            "copies": int(max(1, copies_var.get())),
            "pages": pages_var.get().strip() or None,
            "grayscale": (color_var.get() == "sw"),
            "duplex_mode": duplex_var.get(),
            "media": media_var.get(),
            "orientation": orient_var.get(),
        }

    def _pdf_bytes():
        # We already have the document in memory via fitz; re-rendering to bytes is unnecessary.
        # Use the original source:
        if pdf_blob is not None:
            return pdf_blob
        # If a path was given, read it
        with open(pdf_path, "rb") as f:
            return f.read()

    def _do_preview():
        try:
            preview_pdf(_pdf_bytes())
        except Exception as e:
            messagebox.showerror("Vorschau-Fehler", str(e))

    def _do_print():
        opts = _collect_options()
        try:
            print_pdf_with_options(_pdf_bytes(), **opts)
            messagebox.showinfo("Drucken", "Druckauftrag wurde gesendet.")
        except Exception as e:
            messagebox.showerror("Druck-Fehler", str(e))

    return viewer, win
