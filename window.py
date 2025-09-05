# tk_tabs.py
from io import BytesIO
import json
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

import threading

from dhl_api import api_version_resource, checkout_shopping_chart_png, download_and_unpack, get_shopping_chart_id, struct_address, user_resource

# window.py
from MSSQLDatabase import MSSQLDatabase   # <-- import the class, not the module

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        ...
        # correct way to get a db instance:
        with MSSQLDatabase.connect_with_env() as db:
            # e.g. test connection or store it
            print("Connected OK")

from a4_a6_selector import A4A6Selector

# tk_app_selector_with_textrows.py
import tkinter as tk
from tkinter import ttk

from jtl_api import fetch_orders
from prepare_print_pdf import prepare_pdf_blob
from text_row import TextRow, StatusKnob
import os
import datetime as dt
import hashlib


INTERNETMARKEN_PRODUCTS = [('290', 'Warensendung', 270), ('331', 'Warensendung 1.000 zzgl. Gewichtszuschlag', 355)]
A4_W, A4_H = 210, 297  # DIN A4 aspect ratio

MARKS_PATH = './marks'

def marks_dictionary():
    if not os.path.exists(MARKS_PATH):
        os.makedirs(MARKS_PATH)

class UserCancelledError(Exception): pass

def ok_cancel_dialog(title="Confirm", message="Proceed?"):
    root = tk.Tk()
    root.withdraw()               # hide root window
    try:
        ok = messagebox.askokcancel(title, message, icon="question", default="ok", parent=root)
    finally:
        root.destroy()
    if not ok:
        raise UserCancelledError("User pressed Cancel.")
    return True


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tkinter App — DIN A4/A6 Selector with Status Bar")
        self._center(1000, 560)
        self.minsize(840, 420)
        # optional nicer ttk theme if available
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("aqua")
        except tk.TclError:
            pass
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        
        # ---- Home page ----
        home = ttk.Frame(nb, padding=8)
        nb.add(home, text="Home")

        # Use grid layout instead of vertical packing
        home.columnconfigure(0, weight=1)   # left: selector
        home.columnconfigure(1, weight=4)   # right: text fields
        home.rowconfigure(0, weight=1)

        # selector on the left
        selector_frame = ttk.LabelFrame(home, text="Drucker Papier frei")
        selector_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.selector = A4A6Selector(selector_frame)
        self.selector.pack(fill="both", expand=True)

               # Right: four TextRow panels
        textfields_frame = ttk.LabelFrame(home, text="Notes for each A6 section")
        textfields_frame.grid(row=0, column=1, sticky="nsew")

        grid = ttk.Frame(textfields_frame)
        grid.pack(fill="both", expand=True)

        labels = ["Top-Left", "Top-Right", "Bottom-Left", "Bottom-Right"]
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        self.rows = {}

        for i, (r, c) in enumerate(positions):
            cell = TextRow(grid, title=labels[i])
            cell.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)
            # Connect example button action: paste the label into its text
            self.rows[i] = cell

        # make 2x2 grid stretch
        for r in (0, 1):
            grid.rowconfigure(r, weight=1)
        for c in (0, 1):
            grid.columnconfigure(c, weight=1)

        # ---- Footer for Home ----
        footer = ttk.Frame(home)
        footer.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        footer.columnconfigure(0, weight=1)  # spacer for right alignment

        # Left-side button
        btn_import = ttk.Button(footer, text="Import JTL", command=self._on_import_jtl)
        btn_import.grid(row=0, column=0, sticky="w")
        

        # Right-side buttons
        btn_preview = ttk.Button(footer, text="Vorschau", command=self._on_preview_pdf)

        style = ttk.Style()
        style.configure("Print.TButton",
                        foreground="white",
                        background="#1976D2",
                        padding=6)
        style.map("Print.TButton",
                background=[("active", "#1565C0")])  # darker blue when pressed
        btn_print = ttk.Button(footer, text="Drucken", command=self._print_pdf_blob)

        btn_preview.grid(row=0, column=1, sticky="e", padx=(0, 6))
        btn_print.grid(row=0, column=2, sticky="e")



        # update status when selector changes
        self.selector.on_change = lambda e: print(e)

       # ---- Settings page ----
        settings = ttk.Frame(nb, padding=12)
        nb.add(settings, text="Settings")

        # Group: Sender Adresse
        lf_sender = ttk.LabelFrame(settings, text="Sender Adresse")
        lf_sender.pack(fill="x", pady=(0, 10))

        self.var_sender = tk.StringVar(value=os.getenv("SENDER_ADDR"))   # default empty, can prefill
        entry_sender = ttk.Entry(lf_sender, textvariable=self.var_sender, width=50)
        entry_sender.pack(fill="x", padx=6, pady=4)

        # Group: Lieferung Query
        lf_query = ttk.LabelFrame(settings, text="Lieferung Query")
        lf_query.pack(fill="x", pady=(0, 10))

        row = ttk.Frame(lf_query)
        row.pack(fill="x", pady=6)

        # Checkboxes
        self.var_ls_erstellt = tk.BooleanVar(value=True)     # Lieferschein erstellt
        self.var_shop_best = tk.BooleanVar(value=True)       # Online Shop Bestellung

        ttk.Checkbutton(row, text="Lieferschein erstellt",
                        variable=self.var_ls_erstellt).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(row, text="Online Shop Bestellung",
                        variable=self.var_shop_best).pack(side="left")

        # Days counter
        ttk.Label(row, text="Tage:").pack(side="left", padx=(16, 6))
        self.var_days = tk.IntVar(value=30)
        self.spin_days = ttk.Spinbox(row, from_=1, to=365, width=6,
                                    textvariable=self.var_days, justify="right")
        self.spin_days.pack(side="left")

        # Group: JTL Database
        lf_jtl = ttk.LabelFrame(settings, text="JTL Database")
        lf_jtl.pack(fill="x", pady=(10, 0))

        bar = ttk.Frame(lf_jtl)
        bar.pack(fill="x", pady=6)

        ttk.Label(bar, text="Verbindung:").pack(side="left")

        # colored knob
        self.jtl_knob = StatusKnob(bar, size=12)
        self.jtl_knob.pack(side="left", padx=8)

        # optional: a button to test/update the status
        ttk.Button(bar, text="Test verbinden", command=self._on_test_jtl).pack(side="left", padx=(8, 0))

        # ---- DHL Portokasse API ----
        lf_porto = ttk.LabelFrame(settings, text="DHL Portokasse API")
        lf_porto.pack(fill="x", pady=(0, 10))

        porto_bar = ttk.Frame(lf_porto)
        porto_bar.pack(fill="x", pady=6)

        ttk.Label(porto_bar, text="Verbindung:").pack(side="left")

        self.porto_knob = StatusKnob(porto_bar, size=12)
        self.porto_knob.pack(side="left", padx=8)

        ttk.Button(porto_bar, text="Test verbinden", command=self._on_test_portokasse)\
        .pack(side="left", padx=(8, 0))

        # Info labels
        info = ttk.Frame(lf_porto)
        info.pack(fill="x", pady=(6, 0))

        self.var_wallet = tk.StringVar(value="Wallet: –")
        self.var_issued = tk.StringVar(value="Issued: –")

        ttk.Label(info, textvariable=self.var_wallet).pack(anchor="w")
        ttk.Label(info, textvariable=self.var_issued).pack(anchor="w")
        # ---- Notes page ----
        history = ttk.Frame(nb, padding=12)
        nb.add(history, text="History")
        tk.Text(history, height=12).pack(fill="both", expand=True)


        self._on_test_portokasse()

        self.set_internetmarke_options()
        
        marks_dictionary()

    def _center(self, w, h):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = (sw - w) // 2, (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _update_status(self, selected):
        names = [self.selector.cell_names[i] for i in selected]
        self.status.set("Selected: " + (", ".join(names) if names else "none"))

    def _on_import_jtl(self):
        # Start by entering a MSSQL Connection from .env

        with MSSQLDatabase.connect_with_env() as db:

            # Fetch the latest orders without ShipmentQuote
            data = fetch_orders(db, days=30)

            # Display the addresses in the selected boxes
            for index, c in enumerate(self.selector.get_selected()):
                if len(data) > index:
                    self.rows[c].set_text(data[index])

                    # check if the data is in Germany
                    name, addiditional_name, street, street2, postalcode, city, country = struct_address(self.rows[c].get_text())
                    self.rows[c].auto_select_internetmarke_for_country(country)





    def _load_pdf_blob(self, path: str) -> bytes:

        data = [False, False, False, False]
        poststamp = [False, False, False, False]

        dhl_positions = []
        for c in self.selector.get_selected():
            # set text for pdf preparation
            text = self.rows[c].get_text()
            data[c] = text

            p = self.rows[c].get_internetmarke() 
            if p != '-':
                poststamp[c] = p

                

        return prepare_pdf_blob(send_addr=os.getenv("SENDER_ADDR"), data=data, postmarks=[False, False, False, False])
        

    def _print_pdf_blob(self, ) -> bytes:
        data = [False, False, False, False]
        postmark = [False, False, False, False]

        dhl_positions = []

        # build receiver blocks
        for c in self.selector.get_selected():
            # set text for pdf preparation
            text = self.rows[c].get_text()
            data[c] = text

            p = self.rows[c].get_internetmarke() 
            if p:
                postmark_position = { "receiver": text, "product_id": p, "date": dt.datetime.today().strftime('%Y-%m-%d') }

                hash = hashlib.md5(json.dumps(postmark_position).encode('utf-8')).hexdigest()
                
                # file exists and if open and add to postmarks
                if os.path.exists(f"./marks/{hash}.png"):
                    with open(f"./marks/{hash}.png", 'rb') as f:
                        postmark[c] = f.read() 
                # file does not exist 
                else:
                    postmark_position['hash'] = hash
                    postmark_position['index'] = c
                    # append to dhl_positions
                    dhl_positions.append(postmark_position)

      

        # need to purchase new postmarks
        if len(dhl_positions):
            total_price = 0
            addresses = '\n'.join(map(lambda e: e['receiver'] if e else '', dhl_positions))
            
            message = f"""
                Möchtest du bei DHL {len(dhl_positions)} Marken für {total_price} kaufen?
                {addresses}
            """ 
            
            ok_cancel_dialog(title='kostenpflichtig Kaufen?', message=message)

            access_token, walletBalance, token_type, expires_in, issued_at, external_customer_id, authenticated_user = user_resource()
            # create a shopping chart with id
            shop_order_id = get_shopping_chart_id()

            def internetmark_position(c):
                e = self.rows[c]
                index = e.get_internetmarke_index() 
                if index:
                    index = index - 1
                    return  { "receiver": e.get_text(), "price": INTERNETMARKEN_PRODUCTS[index][2], "product_code": INTERNETMARKEN_PRODUCTS[index][0] }
                else:
                    return False
                
            images = []
            response = 0
            try:
                response = checkout_shopping_chart_png(shop_order_id, list(filter(lambda e: e, list(map(internetmark_position , self.rows)))))
                images = download_and_unpack(response['link'])
            except:
                print(response)
                ok_cancel_dialog('Fehler beim Postmarken kauf', json.loads(response)['description'])
                pass

            for index in range(len(dhl_positions)):
                postmark_index = dhl_positions[index]['index']
                
                # convert python png to buffer 
                buf = BytesIO()
                images[index].save(buf, format='PNG')               # encode to PNG/JPEG/etc.
                img_data = buf.getvalue()   

                # convert image to postmark
                postmark[postmark_index] = img_data

                # save image as binary
                with open(f"./marks/{hash}.png", 'wb') as f:

                    f.write(img_data)
    

        

        pdf_blob = prepare_pdf_blob(send_addr=os.getenv("SENDER_ADDR"), data=data, postmarks=postmark )

        # check for existing postmarks
        # path must be at -> ./marks/md5({'receiver': '', 'product_id': '270', 'date': '2025-09-05'}).png
           
        # open preview window
        # Show the preview + settings window
        from printer import show_pdf_preview_toplevel
        viewer, win = show_pdf_preview_toplevel(self, pdf_blob=pdf_blob, title="Mein PDF Druck")





    def _on_preview_pdf(self):

        # TODO: replace with your real PDF bytes (from your generator or API)
        pdf_blob = self._load_pdf_blob("output.pdf")  # ← any PDF file for testing

        # open preview window
        from pdf_preview import show_pdf_preview_toplevel  # or adjust import
        show_pdf_preview_toplevel(self, pdf_blob=pdf_blob, title="Label-Vorschau")

    def get_lieferung_query(self) -> dict:
        """Read current Lieferung Query settings."""
        return {
            "lieferschein_erstellt": bool(self.var_ls_erstellt.get()),
            "online_shop_bestellung": bool(self.var_shop_best.get()),
            "tage": int(self.var_days.get()),
        }

    def _on_test_jtl(self):
        """Demo: toggle JTL connection knob (replace with real ping)."""
        # TODO: perform your actual DB health check here and set True/False accordingly
        import random
        ok = random.choice([True, False])
        self.jtl_knob.set(ok)



    def set_internetmarke_options(self):
        for i in range(0, len(self.rows)):
            self.rows[i].set_internetmarke_options([('270', 'Warensendung'), ('331', 'Warensendung 1.000 zzgl. Gewichtszuschlag')])

    def _on_test_portokasse(self):
        """Run Portokasse health check in a thread and update knob."""
        # Optional: set to grey while checking
        self.porto_knob.set(None)

        def work():
            ok = api_version_resource()
            access_token, walletBalance, token_type, expires_in, issued_at, external_customer_id, authenticated_user = user_resource()
            self.after(0, lambda: self.porto_knob.set(True if ok else False))

            euro = walletBalance / 100
            self.after(0, self.var_wallet.set(f"Wallet: {euro:.2f} €"))
        
            self.after(0, self.var_issued.set(f"Issued: {issued_at}"))


        threading.Thread(target=work, daemon=True).start()

    def _check_portokasse_api(self) -> bool:
        """
        Placeholder for a real DHL Portokasse API health check.
        Return True if credentials work / API reachable, else False.
        """
        # Example: read creds from env or settings fields (adapt to your app)
        email = os.getenv("DHL_PORTOKASSE_EMAIL", "")
        password = os.getenv("DHL_PORTOKASSE_PASSWORD", "")
        api_key = os.getenv("DHL_PORTOKASSE_API_KEY", "")

        # TODO: implement the real HTTP call here with `requests`.
        # Hints:
        # - Some integrations use session login (email/password), others tokens.
        # - Handle timeouts and non-200 responses.
        # - Never block the UI: this runs in a thread.
        try:
            import requests
            # EXAMPLE ONLY (replace with the real endpoint & auth)
            # resp = requests.get("https://api.example.dhl.de/portokasse/ping",
            #                     headers={"Authorization": f"Bearer {api_key}"},
            #                     timeout=8)
            # return resp.ok
            # For now, simulate success if api_key looks set:
            return bool(api_key or (email and password))
        except Exception:
            return False


if __name__ == "__main__":
    App().mainloop()
