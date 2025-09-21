# mv3d_app.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import os
from base_app import BaseApp
from error_definitions import check_for_error
# Importiere alle Parser
from bhs_log_parser import parse_log as parse_bhs
from bms_log_parser import parse_log as parse_bms
from dpp_log_parser import parse_log as parse_dpp
from plc_log_parser import parse_log as parse_plc
from scs_log_parser import parse_log as parse_scs
from iqtk_log_parser import parse_log as parse_iqtk
from fsm_log_parser import parse_log as parse_fsm

class MV3DApp(BaseApp):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, app_name="MV3D System Analyzer", version="3.1", *args, **kwargs)
        self.all_dfs = []
        self.error_map = {}
        
        self.parser_map = {
            "bhs.log": parse_bhs, "bms.log": parse_bms, "dpp.log": parse_dpp,
            "plc.log": parse_plc, "scs.log": parse_scs, "iqtk.log": parse_iqtk,
            "fsm.log": parse_fsm
        }
        
        self._setup_ui()

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding="10"); main_frame.pack(fill=tk.BOTH, expand=True)
        button_frame = ttk.Frame(main_frame); button_frame.pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="Alle Logs laden (Verzeichnis auswählen)", command=self._load_all_logs).pack(fill=tk.X, padx=5, pady=5)

        tree_frame = ttk.Frame(main_frame); tree_frame.pack(fill=tk.BOTH, expand=True, pady=(10,0))
        self.tree = ttk.Treeview(tree_frame)
        self.tree.tag_configure('error', background='#FFD2D2', foreground='black')
        self.tree.bind("<ButtonRelease-1>", self._on_tree_click)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y); self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _load_all_logs(self):
        dir_path = filedialog.askdirectory(title="Wählen Sie den Ordner mit den Log-Dateien", parent=self)
        if not dir_path: return
        
        files_to_process = [(os.path.join(dir_path, f), p) for f, p in self.parser_map.items() if os.path.exists(os.path.join(dir_path, f))]
        if not files_to_process:
            messagebox.showwarning("Keine Dateien gefunden", "Im Ordner wurden keine der bekannten Log-Dateien gefunden.", parent=self)
            return
        
        self.all_dfs = []
        try:
            for path, parser in files_to_process:
                df = parser(path); self.all_dfs.append(df)
            combined_df = pd.concat(self.all_dfs).sort_values(by="Timestamp").reset_index()
            self._update_treeview(combined_df)
            messagebox.showinfo("Erfolg", f"{len(combined_df)} relevante Einträge aus {len(files_to_process)} Logs geladen.", parent=self)
        except Exception as e:
            messagebox.showerror("Fehler", f"Ein Fehler ist aufgetreten:\n{e}", parent=self)

    def _update_treeview(self, df):
        self.error_map.clear()
        for i in self.tree.get_children(): self.tree.delete(i)
        if not df.empty:
            df['Timestamp'] = pd.to_datetime(df['Timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S.%f').str[:-3]
            self.tree["columns"] = list(df.columns.drop('index'))
            self.tree["show"] = "headings"
            for col in self.tree["columns"]: self.tree.heading(col, text=col)
            self.tree.column("Timestamp", width=180); self.tree.column("Quelle", width=80, anchor='center'); self.tree.column("Ereignis", width=500)
            
            for index, row in df.iterrows():
                tags = ()
                problem, consequence = check_for_error(row['Ereignis'])
                if problem:
                    tags = ('error',)
                    self.error_map[str(index)] = (problem, consequence)
                
                self.tree.insert("", "end", values=list(row.drop('index')), iid=index, tags=tags)
    
    def _on_tree_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id and item_id in self.error_map:
            problem, consequence = self.error_map[item_id]
            self._show_error_explanation(problem, consequence)
            
    def _show_error_explanation(self, problem, consequence):
        win = tk.Toplevel(self); win.title("Fehler-Analyse"); win.geometry("600x300")
        win.transient(self); win.grab_set()
        
        main_frame = ttk.Frame(win); main_frame.pack(fill="both", expand=True)
        
        # KORREKTUR: Verwende ein Standard tk.Text Widget ohne den fehlerhaften background-Parameter
        # Es ist von Natur aus scrollbar, wenn wir eine Scrollbar hinzufügen.
        text_widget = tk.Text(main_frame, wrap=tk.WORD, font=("Helvetica", 10), relief="flat")
        text_widget.pack(side="left", fill="both", expand=True, padx=15, pady=15)
        
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=text_widget.yview)
        scrollbar.pack(side="right", fill="y"); text_widget.config(yscrollcommand=scrollbar.set)
        
        text_widget.tag_configure("bold", font=("Helvetica", 12, "bold"))
        
        text_widget.insert(tk.END, "Was ist das Problem?\n", "bold")
        text_widget.insert(tk.END, f"{problem}\n\n")
        text_widget.insert(tk.END, "Was passiert gerade in der Anlage?\n", "bold")
        text_widget.insert(tk.END, consequence)
        
        # Text kopierbar, aber nicht editierbar machen
        text_widget.config(state="disabled")

        # Trick, um Selektion & Kopieren bei "disabled" zu ermöglichen
        def enable_copy(event):
            text_widget.config(state="normal")
            text_widget.after(50, lambda: text_widget.config(state="disabled"))
        
        text_widget.bind("<Button-1>", enable_copy)