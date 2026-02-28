import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import requests
import os

# Example API endpoint (items list)
API_URL = "https://api.warframe.market/v2/items"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("API Grid Viewer")
        self.geometry("1500x800")

        self.mode = "items"           # either 'items' or 'orders'
        self.slugs = []                # list of slug strings
        # track sort order per column
        self.sort_reverse = {}
        # location for known slug files
        self.slugs_dir = os.path.join(os.getcwd(), "slugs")
        os.makedirs(self.slugs_dir, exist_ok=True)
        self.create_widgets()

    def create_widgets(self):
        # Top frame for controls
        control_frame = ttk.Frame(self)
        control_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(control_frame, text="API URL:").pack(side="left")
        self.url_entry = ttk.Entry(control_frame, width=50)
        self.url_entry.insert(0, API_URL)
        self.url_entry.pack(side="left", padx=5)

        self.fetch_btn = ttk.Button(control_frame, text="Fetch", command=self.fetch_data)
        self.fetch_btn.pack(side="left", padx=5)

        # slug file controls
        ttk.Button(control_frame, text="Load slugs", command=self.load_slugs).pack(side="left", padx=5)
        self.slugs_label = ttk.Label(control_frame, text="0 slugs")
        self.slugs_label.pack(side="left", padx=5)
        self.fetch_orders_btn = ttk.Button(control_frame, text="Fetch Orders", command=self.fetch_orders)
        self.fetch_orders_btn.pack(side="left", padx=5)

        # dropdown of slug files
        self.slug_select_var = tk.StringVar()
        self.slug_combo = ttk.Combobox(control_frame, textvariable=self.slug_select_var,
                                       values=self.list_slug_files(), state="readonly", width=20)
        self.slug_combo.pack(side="left", padx=5)
        self.slug_combo.bind("<<ComboboxSelected>>", lambda e: self.load_slugs_from_path(
            os.path.join(self.slugs_dir, self.slug_select_var.get())))

        # best price only toggle
        self.best_only = tk.BooleanVar(value=True)  # enabled by default
        ttk.Checkbutton(control_frame, text="Best price only", variable=self.best_only,
                        command=lambda: self.populate_tree(show_count=False)).pack(side="left", padx=5)

        ttk.Label(control_frame, text="Filter:").pack(side="left", padx=10)
        self.filter_var = tk.StringVar()
        self.filter_entry = ttk.Entry(control_frame, textvariable=self.filter_var, width=20)
        self.filter_entry.pack(side="left", padx=5)
        # keep the trace id so we can disable/reenable while repopulating
        self.filter_var_trace_id = self.filter_var.trace_add("write", lambda *_: self.apply_filter())

        # Treeview to display data
        self.tree = ttk.Treeview(self, columns=("name", "value"), show="headings")
        self.tree.heading("name", text="Name")
        self.tree.heading("value", text="Value")
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        # progress bar + status label
        self.progress = ttk.Progressbar(self, orient="horizontal", mode="determinate")
        # start hidden; we'll show when needed
        self.progress.pack_forget()
        self.status_label = ttk.Label(self, text="")
        self.status_label.pack(fill="x", padx=10, pady=(0,5))

        # store raw data
        self.raw_data = []

    def fetch_data(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("URL required", "Please enter a valid API URL.")
            return

        self.mode = "items"
        self.fetch_btn.config(state="disabled")
        threading.Thread(target=self._fetch_thread, args=(url,), daemon=True).start()

    def _fetch_thread(self, url):
        # show status
        self.after(0, lambda: self.update_status("Fetching items..."))
        try:
            headers = {
                "accept": "application/json",
                # platform and language headers are useful for some WFM endpoints
                "platform": "pc",
                "language": "en"
            }
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            # Try a few common response shapes for the WFM v2 API
            items = []
            if isinstance(data, dict):
                # common shape: {"payload": {"items": [...]}, ...}
                payload = data.get("payload") or {}
                if isinstance(payload, dict):
                    items = payload.get("items") or payload.get("items", [])
                # handle v2 shape: {"apiVersion":..., "data": [...]}
                items = items or data.get("items") or data.get("payload", {}).get("items") or data.get("data") or []
            elif isinstance(data, list):
                items = data

            # fallback to empty list
            if items is None:
                items = []
            self.raw_data = items
            self.after(0, self.populate_tree)
        except Exception as e:
            try:
                body = getattr(e, 'response', None) and e.response.text or ''
                msg = f"{e}\n{body}"
            except Exception:
                msg = str(e)
            self.after(0, lambda: self.update_status(f"Fetch error: {msg}"))
        finally:
            self.after(0, lambda: self.fetch_btn.config(state="normal"))

    # slug file handling ------------------------------------------------
    def list_slug_files(self):
        import os
        try:
            return [f for f in os.listdir(self.slugs_dir) if f.lower().endswith('.txt')]
        except Exception:
            return []

    def load_slugs_from_path(self, path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                self.slugs = [line.strip() for line in fh if line.strip()]
            self.slugs_label.config(text=f"{len(self.slugs)} slugs")
        except Exception as e:
            messagebox.showerror("Load slugs error", str(e))

    def load_slugs(self):
        path = filedialog.askopenfilename(filetypes=[("Text files","*.txt"), ("All files","*.*")])
        if not path:
            return
        # simply read the file; do not copy or modify any slug directory
        try:
            self.load_slugs_from_path(path)
        except Exception as e:
            messagebox.showerror("Load slugs error", str(e))

    def fetch_orders(self):
        if not self.slugs:
            messagebox.showwarning("No slugs", "Load a slug file first.")
            return
        self.fetch_orders_btn.config(state="disabled")
        threading.Thread(target=self._fetch_orders_thread, daemon=True).start()

    def _fetch_orders_thread(self):
        base = "https://api.warframe.market/v2/orders/item/{slug}/top"
        headers = {"accept": "application/json", "platform": "pc", "language": "en"}
        orders = []
        total = len(self.slugs)
        # initialize progress
        self.after(0, self.show_progress)
        self.after(0, lambda: self.progress.config(maximum=total, value=0))
        self.after(0, lambda: self.update_status(f"Fetching orders 0/{total}"))
        for idx, slug in enumerate(self.slugs, start=1):
            try:
                resp = requests.get(base.format(slug=slug), headers=headers, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                d = data.get("data") or {}
                # only include sell orders
                for order in d.get("sell", []):
                    orders.append({
                        "slug": slug,
                        "type": "sell",
                        "platinum": order.get("platinum"),
                        "quantity": order.get("quantity"),
                    })
            except Exception as e:
                print("order fetch error", slug, e)
            # update progress
            self.after(0, lambda i=idx: self.progress.step(1))
            self.after(0, lambda i=idx: self.update_status(f"Fetching orders {i}/{total}"))
        self.raw_data = orders
        self.mode = "orders"
        self.after(0, self.populate_tree)
        self.after(0, lambda: self.fetch_orders_btn.config(state="normal"))
        self.after(0, lambda: self.update_status("Fetch complete", duration=3000))
        self.after(0, self.hide_progress)
        self.after(0, lambda: self.progress.config(value=0))

    def _insert_rows(self, data_list):
        """Helper: insert rows from data_list according to current mode."""
        if self.mode == "orders":
            for item in data_list:
                slug = item.get("slug")
                typ = item.get("type")
                price = item.get("platinum")
                qty = item.get("quantity")
                self.tree.insert("", "end", values=(slug, typ, price, qty))
        else:
            for item in data_list:
                name = None
                slug = None
                if isinstance(item, dict):
                    name = (
                        item.get("i18n", {}).get("en", {}).get("name")
                        or item.get("item_name")
                        or item.get("name")
                        or (item.get("item") and item.get("item").get("name"))
                        or item.get("url_name")
                        or item.get("slug")
                    )
                    slug = item.get("slug") or item.get("url_name") or ""
                if not name:
                    name = str(item)
                # display slug in second column when not orders
                self.tree.insert("", "end", values=(name, slug))

    def populate_tree(self, show_count=True):
        # clear existing rows
        for row in self.tree.get_children():
            self.tree.delete(row)

        # reconfigure columns based on mode
        if self.mode == "orders":
            self.tree.config(columns=("slug", "type", "price", "quantity"))
            self.tree.heading("slug", text="Slug", command=lambda c="slug": self.sort_by(c))
            self.tree.heading("type", text="Type", command=lambda c="type": self.sort_by(c))
            self.tree.heading("price", text="Plat", command=lambda c="price": self.sort_by(c))
            self.tree.heading("quantity", text="Qty", command=lambda c="quantity": self.sort_by(c))
        else:
            self.tree.config(columns=("name", "value"))
            self.tree.heading("name", text="Name", command=lambda c="name": self.sort_by(c))
            self.tree.heading("value", text="Slug", command=lambda c="value": self.sort_by(c))

        # decide which data to show (best-only filter applies to orders)
        data_list = self.raw_data
        if self.mode == "orders" and self.best_only.get():
            # pick smallest platinum order per slug
            best = {}
            for o in data_list:
                slug = o.get("slug")
                plat = o.get("platinum") if isinstance(o.get("platinum"), (int, float)) else float("inf")
                if slug not in best or plat < (best[slug].get("platinum") or float("inf")):
                    best[slug] = o
            data_list = list(best.values())
        self._insert_rows(data_list)
        if self.filter_var.get().strip():
            self.apply_filter()

        # inform user via status label
        if show_count:
            try:
                count = len(self.raw_data)
                if count:
                    message = f"Loaded {count} {'orders' if self.mode=='orders' else 'items'}"
                    self.update_status(message, duration=3000)
            except Exception:
                pass

    def update_status(self, text, duration=None):
        self.status_label.config(text=text)
        if duration:
            self.after(duration, lambda: self.status_label.config(text=""))

    def show_progress(self):
        """Make the progress bar visible."""
        self.progress.pack(fill="x", padx=10, pady=(0,2))

    def hide_progress(self):
        """Hide the progress bar."""
        self.progress.pack_forget()

    def sort_by(self, col):
        """Sort currently displayed rows by column `col`."""
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        # detect numeric
        try:
            items = [(float(v), k) for v, k in items]
        except Exception:
            items = [(v.lower(), k) for v, k in items]
        reverse = self.sort_reverse.get(col, False)
        items.sort(reverse=reverse)
        for index, (_, k) in enumerate(items):
            self.tree.move(k, '', index)
        self.sort_reverse[col] = not reverse

    def apply_filter(self):
        filter_text = self.filter_var.get().lower().strip()
        # clear tree and rebuild from raw data with current filter
        for row in self.tree.get_children():
            self.tree.delete(row)
        # decide which data to show
        data_list = self.raw_data
        if self.mode == "orders" and self.best_only.get():
            best = {}
            for o in data_list:
                slug = o.get("slug")
                plat = o.get("platinum") if isinstance(o.get("platinum"), (int, float)) else float("inf")
                if slug not in best or plat < (best[slug].get("platinum") or float("inf")):
                    best[slug] = o
            data_list = list(best.values())
        # filter and insert rows
        if filter_text:
            for item in data_list:
                values = self._get_item_values(item)
                if filter_text in str(values[0]).lower():
                    self.tree.insert("", "end", values=values)
        else:
            # no filter: show all
            self._insert_rows(data_list)

    def _get_item_values(self, item):
        """Extract display values from an item for the current mode."""
        if self.mode == "orders":
            return (item.get("slug"), item.get("type"), item.get("platinum"), item.get("quantity"))
        else:
            name = (
                item.get("i18n", {}).get("en", {}).get("name")
                or item.get("item_name")
                or item.get("name")
                or (item.get("item") and item.get("item").get("name"))
                or item.get("url_name")
                or item.get("slug")
            )
            if not name:
                name = str(item)
            slug = item.get("slug") or item.get("url_name") or ""
            return (name, slug)

if __name__ == "__main__":
    app = App()
    app.mainloop()
