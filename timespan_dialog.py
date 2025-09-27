# timespan_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime

class TimespanDialog(tk.Toplevel):
    def __init__(self, parent, available_start=None, available_end=None, total_entries=0):
        super().__init__(parent)
        self.title("Analyse-Zeitraum festlegen")
        self.transient(parent); self.grab_set()
        
        self.result = None
        self.available_start = available_start
        self.available_end = available_end
        self.total_entries = total_entries

        self._setup_widgets()
        
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _setup_widgets(self):
        main_frame = ttk.Frame(self, padding=20); main_frame.pack(fill=tk.BOTH, expand=True)

        info_frame = ttk.LabelFrame(main_frame, text="Vorschau der verfügbaren Daten", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 15))
        
        start_text = self.available_start.strftime('%d.%m.%Y %H:%M:%S') if self.available_start else "N/A"
        end_text = self.available_end.strftime('%d.%m.%Y %H:%M:%S') if self.available_end else "N/A"
        
        ttk.Label(info_frame, text=f"Frühester Eintrag:").grid(row=0, column=0, sticky="w")
        ttk.Label(info_frame, text=f"{start_text}").grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(info_frame, text=f"Spätester Eintrag:").grid(row=1, column=0, sticky="w")
        ttk.Label(info_frame, text=f"{end_text}").grid(row=1, column=1, sticky="w", padx=5)
        ttk.Label(info_frame, text=f"Gefundene Einträge gesamt:").grid(row=2, column=0, sticky="w")
        ttk.Label(info_frame, text=f"{self.total_entries:,}".replace(",", ".")).grid(row=2, column=1, sticky="w", padx=5)

        self.start_frame = ttk.Frame(main_frame); self.start_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.start_frame, text="Start:").pack(side=tk.LEFT, padx=5)
        self.start_date_entry = DateEntry(self.start_frame, date_pattern='dd.mm.yyyy', locale='de_DE')
        self.start_date_entry.pack(side=tk.LEFT, padx=5)
        self.start_time_entry = ttk.Entry(self.start_frame, width=8); self.start_time_entry.pack(side=tk.LEFT, padx=5)

        self.end_frame = ttk.Frame(main_frame); self.end_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.end_frame, text="Ende: ").pack(side=tk.LEFT, padx=5)
        self.end_date_entry = DateEntry(self.end_frame, date_pattern='dd.mm.yyyy', locale='de_DE')
        self.end_date_entry.pack(side=tk.LEFT, padx=5)
        self.end_time_entry = ttk.Entry(self.end_frame, width=8); self.end_time_entry.pack(side=tk.LEFT, padx=5)

        if self.available_start:
            self.start_date_entry.set_date(self.available_start.date())
            self.start_time_entry.insert(0, self.available_start.strftime('%H:%M:%S'))
        if self.available_end:
            self.end_date_entry.set_date(self.available_end.date())
            self.end_time_entry.insert(0, self.available_end.strftime('%H:%M:%S'))

        self.load_all_var = tk.BooleanVar(value=False)
        self.load_all_check = ttk.Checkbutton(main_frame, text="Ganzen Zeitraum laden (kann lange dauern!)", variable=self.load_all_var, command=self._toggle_entries)
        self.load_all_check.pack(pady=10)
        
        button_frame = ttk.Frame(main_frame); button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Analyse starten", command=self._on_start).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Abbrechen", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def _toggle_entries(self):
        state = "disabled" if self.load_all_var.get() else "normal"
        self.start_date_entry.config(state=state); self.start_time_entry.config(state=state)
        self.end_date_entry.config(state=state); self.end_time_entry.config(state=state)

    def _on_start(self):
        if self.load_all_var.get():
            self.result = {"load_all": True}; self.destroy(); return
        try:
            start_date = self.start_date_entry.get_date()
            end_date = self.end_date_entry.get_date()
            start_time = datetime.strptime(self.start_time_entry.get(), '%H:%M:%S').time()
            end_time = datetime.strptime(self.end_time_entry.get(), '%H:%M:%S').time()
            self.result = {"load_all": False, "start": datetime.combine(start_date, start_time), "end": datetime.combine(end_date, end_time)}
            if self.result["end"] < self.result["start"]:
                messagebox.showerror("Ungültiger Zeitraum", "Das End-Datum darf nicht vor dem Start-Datum liegen.", parent=self)
                self.result = None; return
            self.destroy()
        except ValueError:
            messagebox.showerror("Ungültiges Zeitformat", "Bitte geben Sie die Zeit im Format HH:MM:SS ein.", parent=self)
            self.result = None

    def show(self):
        self.wm_deiconify(); self.wait_window(); return self.result