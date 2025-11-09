# ftp_file_selection_dialog.py
import tkinter as tk
from tkinter import ttk
import os

class FTPFileSelectionDialog(tk.Toplevel):
    def __init__(self, parent, file_list_map):
        """
        Initialisiert den Dialog.
        file_list_map ist ein Dictionary: {'system_name': ['file1', 'file2'], ...}
        """
        super().__init__(parent)
        self.title("FTP-Dateiauswahl")
        self.geometry("800x600")
        self.transient(parent)
        self.grab_set()
        
        self.selected_files_map = {}
        self.vars = {} # Speichert die tk.BooleanVar für jede Checkbox

        # Erstelle ein Notebook (Tabs) für jedes System
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for system_name, file_list in file_list_map.items():
            if not file_list:
                continue

            # Tab-Frame
            sys_frame = ttk.Frame(notebook, padding=10)
            notebook.add(sys_frame, text=f"{system_name} ({len(file_list)})")
            
            # Container für Buttons
            select_btn_frame = ttk.Frame(sys_frame)
            select_btn_frame.pack(fill=tk.X, pady=5)
            
            ttk.Button(select_btn_frame, text="Alle auswählen", command=lambda s=system_name: self._select_all(s, True)).pack(side=tk.LEFT)
            ttk.Button(select_btn_frame, text="Alle abwählen", command=lambda s=system_name: self._select_all(s, False)).pack(side=tk.LEFT, padx=5)

            # Frame für Checkboxen in einem Scroll-Bereich
            canvas = tk.Canvas(sys_frame, borderwidth=0, highlightthickness=0)
            scrollbar = ttk.Scrollbar(sys_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e, c=canvas: c.configure(scrollregion=c.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            self.vars[system_name] = {}
            
            # Checkboxen für diese System-Liste erstellen
            for file_path in sorted(file_list):
                # Zeige nur den relativen Pfad an, nicht den vollen Serverpfad
                display_name = os.path.basename(file_path)
                
                var = tk.BooleanVar(value=True) # Standardmäßig alle auswählen
                cb = ttk.Checkbutton(scrollable_frame, text=display_name, variable=var, onvalue=True, offvalue=False)
                cb.pack(anchor="w", padx=5)
                self.vars[system_name][file_path] = var

        # Buttons (OK/Abbrechen)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(btn_frame, text="Auswahl herunterladen", command=self._on_submit, style="Accent.TButton").pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Abbrechen", command=self._on_cancel).pack(side=tk.RIGHT)
        
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window(self)

    def _select_all(self, system_name, value):
        """Wählt alle Checkboxen in einem Tab aus oder ab."""
        if system_name in self.vars:
            for var in self.vars[system_name].values():
                var.set(value)

    def _on_submit(self):
        """Sammelt alle ausgewählten Dateien."""
        for system_name, file_vars in self.vars.items():
            selected_for_system = []
            for file_path, var in file_vars.items():
                if var.get():
                    selected_for_system.append(file_path)
            
            if selected_for_system:
                self.selected_files_map[system_name] = selected_for_system
                
        self.destroy()

    def _on_cancel(self):
        """Bricht ab und gibt eine leere Map zurück."""
        self.selected_files_map = {}
        self.destroy()

    def show(self):
        """Gibt die Map der ausgewählten Dateien zurück."""
        return self.selected_files_map