# advanced_search_dialog.py
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry

class AdvancedSearchDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Erweiterte Suche"); self.geometry("450x280"); self.transient(parent); self.grab_set()
        self.result = None
        frame = ttk.Frame(self, padding="10"); frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="BagID enthält:").grid(row=0, column=0, sticky="w", pady=5)
        self.bag_id_entry = ttk.Entry(frame, width=30); self.bag_id_entry.grid(row=0, column=1)
        ttk.Label(frame, text="IATA enthält:").grid(row=1, column=0, sticky="w", pady=5)
        self.iata_entry = ttk.Entry(frame, width=30); self.iata_entry.grid(row=1, column=1)
        ttk.Label(frame, text="Datum von:").grid(row=2, column=0, sticky="w", pady=5)
        self.start_date_entry = DateEntry(frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.start_date_entry.grid(row=2, column=1, sticky="w")
        ttk.Label(frame, text="Datum bis:").grid(row=3, column=0, sticky="w", pady=5)
        self.end_date_entry = DateEntry(frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.end_date_entry.grid(row=3, column=1, sticky="w")
        self.oms_only_var = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Nur Einträge mit OMS-Verbindung", variable=self.oms_only_var).grid(row=4, column=0, columnspan=2, sticky="w", pady=10)
        button_frame = ttk.Frame(frame); button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Suchen", command=self._on_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Abbrechen", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def _on_search(self):
        self.result = {"bag_id": self.bag_id_entry.get(), "iata": self.iata_entry.get(), "start_date": self.start_date_entry.get(), "end_date": self.end_date_entry.get(), "oms_only": self.oms_only_var.get()}
        self.destroy()

    def show(self):
        self.wm_deiconify(); self.wait_window(); return self.result