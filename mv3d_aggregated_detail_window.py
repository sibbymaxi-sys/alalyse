# mv3d_aggregated_detail_window.py
# Zeigt alle Roh-Logs an, die zu einer aggregierten Zeile gehören.

import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import sys

try:
    # (Dieser Import wird für den Doppelklick *innerhalb* dieses Fensters benötigt)
    from mv3d_casefile_window import MV3DCasefileWindow
except ImportError:
    print("WARNUNG: mv3d_casefile_window.py nicht gefunden. Detailansicht deaktiviert.")
    class MV3DCasefileWindow: # Fallback
        def __init__(self, parent, selected_row, raw_df):
            messagebox.showerror("Fehler", "Detailfenster (mv3d_casefile_window.py) nicht geladen.", parent=parent)
            win = tk.Toplevel(parent); win.title("Fehler"); ttk.Label(win, text="Detailfenster nicht geladen.").pack(padx=20, pady=20)


class MV3DAggregatedDetailWindow(tk.Toplevel):
    def __init__(self, parent, incidents_df, raw_df, filter_severity, filter_event, filter_source):
        """
        Initialisiert das Detailfenster.
        - parent: Das Hauptfenster (MV3DApp)
        - incidents_df: Das (potenziell riesige) DataFrame mit *allen* Roh-Fehlern (z.B. 56k Zeilen)
        - raw_df: Das DataFrame mit *allen* Logzeilen (für den Kontext-Doppelklick)
        - filter_severity: Der Schweregrad der angeklickten Zeile (z.B. "FAULT")
        - filter_event: Der Event-Text der angeklickten Zeile (z.B. "Hardware Error")
        - filter_source: Die Quelldatei der angeklickten Zeile (z.B. "dmesg")
        """
        super().__init__(parent)
        self.title(f"Detail: [{filter_severity}] {filter_event} ({filter_source})")
        self.geometry("1100x700")
        self.transient(parent)
        self.grab_set()

        self.raw_df = raw_df # Referenz für den Kontext-Doppelklick
        
        # Filtere die 56k+ Fehler auf die, die zu dieser Gruppe gehören
        self.detail_df = incidents_df[
            (incidents_df['Severity'] == filter_severity) &
            (incidents_df['Event'] == filter_event) &
            (incidents_df['SourceFile'] == filter_source)
        ].copy()

        self._setup_ui()
        self._populate_tree()

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        info_label = ttk.Label(main_frame, text=f"{len(self.detail_df)} Vorkommen gefunden, sortiert von neu nach alt.")
        info_label.pack(anchor="w")

        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Einfachere Tabelle: Zeigt nur Zeitstempel und Original-Log
        self.tree = ttk.Treeview(tree_frame, columns=("Timestamp", "OriginalLog"), show="headings")
        self.tree.heading("Timestamp", text="Zeitpunkt"); self.tree.column("Timestamp", width=170, anchor="w")
        self.tree.heading("OriginalLog", text="Original Log-Eintrag"); self.tree.column("OriginalLog", width=800)
        
        # WICHTIG: Doppelklick ruft hier das *alte* Detailfenster auf (für den Kontext)
        self.tree.bind("<Double-1>", self._on_item_select)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _populate_tree(self):
        if self.detail_df.empty:
            return
            
        # Sortiere, um die neuesten Einträge oben anzuzeigen
        df_sorted = self.detail_df.sort_values(by="Timestamp", ascending=False)

        for index, row in df_sorted.iterrows():
            ts_str = row['Timestamp'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['Timestamp']) else 'N/A'
            
            # WICHTIG: Die IID muss der *Original-Index* aus dem DataFrame sein
            # damit der Doppelklick auf raw_df funktioniert.
            self.tree.insert("", "end", iid=index, values=(
                ts_str, 
                row['OriginalLog']
            ))

    def _on_item_select(self, event):
        """
        Doppelklick-Handler: Öffnet das *Kontext*-Fenster (mv3d_casefile_window).
        """
        selected_item_iid = self.tree.focus()
        if not selected_item_iid: return
            
        try:
            iid_int = int(selected_item_iid)
            
            # Finde die Zeile im *originalen raw_df*
            if iid_int in self.raw_df.index:
                selected_raw_row = self.raw_df.loc[iid_int]
                # Öffne das Kontext-Fenster
                MV3DCasefileWindow(self, selected_raw_row, self.raw_df)
            else:
                 messagebox.showwarning("Fehler", "Zugehöriger Rohdaten-Eintrag nicht gefunden.", parent=self)
        
        except (ValueError, KeyError, AttributeError, IndexError) as e:
            print(f"Fehler Öffnen Kontext-Fenster (IID: {selected_item_iid}): {e}\n{traceback.format_exc()}")
            messagebox.showwarning("Fehler", "Kontext-Ansicht nicht möglich.", parent=self)