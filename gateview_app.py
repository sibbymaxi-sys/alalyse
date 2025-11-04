# gateview_app.py
print("--- [V23-FIX] gateview_app.py wird geladen (Neuer Journey-Parser & Doppelklick Tab 2 & AttributeError-Fix) ... ---")

import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import pandas as pd
import threading
import os
import re
import sys
from datetime import datetime
import traceback
import multiprocessing
import subprocess

try:
    import sv_ttk
    from tkcalendar import DateEntry
    
    # --- KORRIGIERTE IMPORTE ---
    from log_parser import parse_log_file         # Für Scanner/OMS (.log)
    import plclog_journey_parser                  # NEU: Für SPS-Journeys (PlcLog.csv)
    import plclog_csv_parser                      # Für SPS-Fehler (PlcLog_0.csv)
    
    # --- NEU: Importiere die SPS-Konsolidierung ---
    from data_processor import consolidate_journeys, consolidate_plc_journeys, FINAL_JOURNEY_COLS
    
    from advanced_search_dialog import AdvancedSearchDialog
    from base_app import BaseApp
    import config_manager as cfg
    from ftp_dialog_advanced import AdvancedFTPDialog
    from ftp_client import SFTPClient
    from sftp_log_window import SFTPLogWindow
    from help_texts import GATEVIEW_HELP_TEXT
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.enums import TA_LEFT
    from system_analyzer_app import SystemAnalyzerApp
except ImportError as e:
    with open("gateview_crash_report.log", "w", encoding='utf-8') as f:
        f.write(f"Ein kritischer Import-Fehler ist aufgetreten:\n\nDie Datei '{e.name}.py' oder die Bibliothek '{e.name}' konnte nicht gefunden werden.\n\n")
        f.write(traceback.format_exc())
    tk.Tk().withdraw() 
    messagebox.showerror("Kritischer Import-Fehler", 
                         f"Die Datei '{e.name}.py' konnte nicht gefunden werden.\n\n"
                         "Das Programm wird jetzt beendet.")
    sys.exit(1)

class GateViewApp(BaseApp):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, app_name="GateView Analyzer", version="1.0", *args, **kwargs)
        # Scanner/OMS Daten
        self.raw_df = pd.DataFrame()
        self.journeys_df = pd.DataFrame()
        
        # Getrennte SPS-Daten
        # --- KORREKTUR DER TYPOS (V22) ---
        self.plc_raw_df = pd.DataFrame() # Rohdaten für Doppelklick
        self.plc_journeys_df = pd.DataFrame() # Zusammengefasste Daten für Tab 2
        self.plc_error_df = pd.DataFrame()
        
        self.loading_win = None
        self._setup_ui()

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding="10"); main_frame.pack(fill=tk.BOTH, expand=True)
        
        # --- Button-Frame (Angepasst mit "Letzter Tag"-Button) ---
        button_frame = ttk.Frame(main_frame); button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="1a. Komplette Logs laden", command=lambda: self._load_from_dialog(mode="scanner_full")).pack(side=tk.LEFT, padx=(5,0))
        ttk.Button(button_frame, text="1b. Letzten Tag laden", command=lambda: self._load_from_dialog(mode="scanner_last_day"), style='Accent.TButton').pack(side=tk.LEFT, padx=(5,5))
        
        self.oms_button = ttk.Button(button_frame, text="2. OMS-Log hinzufügen", command=lambda: self._load_from_dialog(mode="oms"), state="disabled"); self.oms_button.pack(side=tk.LEFT, padx=5)
        
        # --- KORRIGIERTE BUTTON-NAMEN ---
        ttk.Button(button_frame, text="3. SPS-Journeys laden (CSV)", command=self._load_plc_journeys_from_dialog, style='Accent.TButton').pack(side=tk.LEFT, padx=(15, 5))
        ttk.Button(button_frame, text="4. SPS-Fehler laden (CSV)", command=self._load_plc_errors_from_dialog, style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="System-Analyse", command=self._launch_system_analyzer).pack(side=tk.LEFT, padx=(15, 5))
        self.search_button = ttk.Button(button_frame, text="Erweiterte Suche", command=self._open_advanced_search); self.search_button.pack(side=tk.LEFT, padx=5)
        
        # --- Filter-Frame (nur für Tab 1) ---
        filter_frame = ttk.Frame(main_frame, padding=(0, 5)); filter_frame.pack(fill=tk.X, pady=(10,0))
        ttk.Label(filter_frame, text="Filter (nur Gepäck-Analyse):").pack(side=tk.LEFT, padx=(0, 5)); ttk.Label(filter_frame, text="BagID:").pack(side=tk.LEFT, padx=(10, 5)); self.bag_id_filter = ttk.Combobox(filter_frame, width=15); self.bag_id_filter.pack(side=tk.LEFT); ttk.Label(filter_frame, text="IATA:").pack(side=tk.LEFT, padx=(10, 5)); self.iata_filter = ttk.Combobox(filter_frame, width=10); self.iata_filter.pack(side=tk.LEFT); self.iata_filter.bind("<<ComboboxSelected>>", self._apply_filters); ttk.Button(filter_frame, text="Anwenden", command=self._apply_filters).pack(side=tk.LEFT, padx=5); ttk.Button(filter_frame, text="Zurücksetzen", command=self._reset_filters).pack(side=tk.LEFT, padx=5)
        
        # --- Notebook für 3 Tabs ---
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(5,0))
        
        # --- TAB 1: Gepäck-Analyse (Scanner/OMS) ---
        tab1_frame = ttk.Frame(self.notebook, padding=(0, 5))
        self.notebook.add(tab1_frame, text="Gepäck-Analyse (Scanner/OMS)")
        
        tree_frame = ttk.Frame(tab1_frame); tree_frame.pack(fill=tk.BOTH, expand=True, pady=(5,0))
        self.tree = ttk.Treeview(tree_frame); scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set); scrollbar.pack(side=tk.RIGHT, fill=tk.Y); self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); self.tree.bind("<Double-1>", self._on_item_double_click)

        # --- TAB 2: SPS-Journeys (aus .csv) ---
        tab2_frame = ttk.Frame(self.notebook, padding=(0, 5))
        self.notebook.add(tab2_frame, text="SPS-Journeys (PlcLog.csv)")
        
        plc_journey_tree_frame = ttk.Frame(tab2_frame); plc_journey_tree_frame.pack(fill=tk.BOTH, expand=True, pady=(5,0))
        
        # --- KORRIGIERTE SPALTEN (Passend zur neuen Konsolidierung) ---
        plc_journey_cols = ("plc_time", "iata", "klartext", "decision", "scanner_time")
        self.plc_journey_tree = ttk.Treeview(plc_journey_tree_frame, columns=plc_journey_cols, show="headings")
        self.plc_journey_tree.heading("plc_time", text="SPS Zeit"); self.plc_journey_tree.column("plc_time", width=170)
        self.plc_journey_tree.heading("iata", text="IATA"); self.plc_journey_tree.column("iata", width=100)
        self.plc_journey_tree.heading("klartext", text="Beschreibung"); self.plc_journey_tree.column("klartext", width=300)
        self.plc_journey_tree.heading("decision", text="Finale Entscheidung"); self.plc_journey_tree.column("decision", width=150)
        self.plc_journey_tree.heading("scanner_time", text="Nächste Scanner-Zeit"); self.plc_journey_tree.column("scanner_time", width=170)
        
        plc_journey_scrollbar = ttk.Scrollbar(plc_journey_tree_frame, orient="vertical", command=self.plc_journey_tree.yview); self.plc_journey_tree.configure(yscrollcommand=plc_journey_scrollbar.set); plc_journey_scrollbar.pack(side=tk.RIGHT, fill=tk.Y); self.plc_journey_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # --- NEU: Doppelklick für Tab 2 ---
        self.plc_journey_tree.bind("<Double-1>", self._on_plc_item_double_click)


        # --- TAB 3: SPS-Fehler (aus .csv) ---
        tab3_frame = ttk.Frame(self.notebook, padding=(0, 5))
        self.notebook.add(tab3_frame, text="SPS-Fehler (PlcLog_0.csv)")
        
        plc_error_tree_frame = ttk.Frame(tab3_frame); plc_error_tree_frame.pack(fill=tk.BOTH, expand=True, pady=(5,0))
        
        plc_error_cols = ("plc_time", "severity", "klartext", "original_log")
        self.plc_error_tree = ttk.Treeview(plc_error_tree_frame, columns=plc_error_cols, show="headings")
        self.plc_error_tree.heading("plc_time", text="SPS Fehler-Zeit"); self.plc_error_tree.column("plc_time", width=170)
        self.plc_error_tree.heading("severity", text="Schweregrad"); self.plc_error_tree.column("severity", width=80)
        self.plc_error_tree.heading("klartext", text="Fehlermeldung"); self.plc_error_tree.column("klartext", width=400)
        self.plc_error_tree.heading("original_log", text="Original-Log"); self.plc_error_tree.column("original_log", width=400)
        
        plc_error_scrollbar = ttk.Scrollbar(plc_error_tree_frame, orient="vertical", command=self.plc_error_tree.yview); self.plc_error_tree.configure(yscrollcommand=plc_error_scrollbar.set); plc_error_scrollbar.pack(side=tk.RIGHT, fill=tk.Y); self.plc_error_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # --- Statusleiste ---
        self.status_label = ttk.Label(self.status_bar, text="Bereit."); self.status_label.pack(side=tk.LEFT, padx=5)

    def _launch_system_analyzer(self):
        new_window = tk.Toplevel(self)
        new_window.title("Eigenständige System-Analyse (ClearScan)")
        new_window.geometry("1100x700")
        SystemAnalyzerApp(new_window)
    
    def _show_help_window(self):
        help_win = tk.Toplevel(self); help_win.title("Anleitung - GateView Analyzer"); help_win.geometry("800x600"); help_win.transient(self); help_win.grab_set()
        text_area = scrolledtext.ScrolledText(help_win, wrap=tk.WORD, font=("Helvetica", 10), padx=10, pady=10); text_area.pack(expand=True, fill=tk.BOTH)
        text_area.insert(tk.INSERT, GATEVIEW_HELP_TEXT); text_area.config(state="disabled")

    def _open_ftp_dialog(self):
        dialog = AdvancedFTPDialog(self, app_name="gateview")
        ftp_details = dialog.show()
        if ftp_details:
            log_win = SFTPLogWindow(self)
            thread = threading.Thread(target=self._run_sftp_download, args=(ftp_details, log_win), daemon=True)
            thread.start()

    def _run_sftp_download(self, profile, log_win):
        local_dir = os.path.join(os.getcwd(), "logs", "gateview_download")
        os.makedirs(local_dir, exist_ok=True)
        targets = profile.get("targets", {})
        all_downloaded_files = []; has_errors = False
        def log_callback(message): self.after(0, log_win.log, message)
        
        profile_name = profile.get("name", "") 
        
        for system_name, details in targets.items():
            # ... (Rest der Download-Logik bleibt gleich) ...
            pass 

        # ... (Rest der Download-Logik bleibt gleich) ...
            
        # NEUE LOGIK: Entscheiden, welche Lade-Funktion aufgerufen wird
        if "SPS-Journeys" in profile_name: # Zielt auf .csv (Journeys)
             self.after(0, self._start_plc_journey_loading, all_downloaded_files)
        elif "SPS-Fehler" in profile_name: # Zielt auf .csv (Errors)
             self.after(0, self._start_plc_error_loading, all_downloaded_files)
        elif all_downloaded_files:
            log_callback("Download abgeschlossen. Starte Gepäck-Analyse...")
            self.after(0, self.on_ftp_download_complete, all_downloaded_files, "scanner_full")
        elif not all_downloaded_files and has_errors: 
            log_callback("Download-Prozess mit Fehlern abgeschlossen.")
        else: 
            log_callback("Keine Dateien zum Herunterladen gefunden.")
        self.after(3000, log_win.close_window)


    def on_ftp_download_complete(self, downloaded_files, mode="scanner_full"):
        # Diese Funktion ist für Scanner/OMS (TAB 1)
        messagebox.showinfo("Download Abgeschlossen", f"{len(downloaded_files)} Datei(en) heruntergeladen.\nAnalyse (Scanner/OMS) wird gestartet.", parent=self)
        self.raw_df = pd.DataFrame(); self._start_loading_process(downloaded_files, mode)

    def _start_loading_process(self, file_paths, mode):
        # Diese Funktion ist für Scanner/OMS (TAB 1)
        # NEU: 'mode' wird akzeptiert
        self._create_loading_window()
        thread = threading.Thread(target=self._load_and_process_files, args=(file_paths, mode), daemon=True); thread.start()
        self.after(100, self._check_thread, thread, "scanner")

    def _load_from_dialog(self, mode):
        # Diese Funktion ist für Scanner/OMS (TAB 1)
        # NEU: 'mode' wird übergeben ("scanner_full", "scanner_last_day" oder "oms")
        config = cfg.load_config()
        last_dir = config.get("last_gateview_dir", os.getcwd())
        
        title = "OMS-Log auswählen"
        file_types = (("Logdateien", "*.log"), ("Alle Dateien", "*.*"))
        
        if mode.startswith("scanner"):
            title = "Scanner-Log auswählen"
            
        file_path = filedialog.askopenfilename(title=title, initialdir=last_dir, filetypes=file_types)
        if not file_path: return
        
        config["last_gateview_dir"] = os.path.dirname(file_path); cfg.save_config(config)
        
        if mode.startswith("scanner"): # "scanner_full" oder "scanner_last_day"
            self.raw_df = pd.DataFrame() # Setzt Scanner-Logs zurück
            
        self._start_loading_process([file_path], mode)

    # --- NEUE/ANGEPASSTE FUNKTIONEN FÜR SPS-LOGS (TAB 2 & 3) ---
    
    def _load_plc_journeys_from_dialog(self):
        """Öffnet einen Dialog NUR für PlcLog.csv (Journeys)."""
        file_path = filedialog.askopenfilename(
            title="SPS-Journeys (PlcLog.csv) auswählen", 
            filetypes=(("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*"))
        )
        if not file_path: return
        self._start_plc_journey_loading([file_path])

    def _load_plc_errors_from_dialog(self):
        """Öffnet einen Dialog NUR für plclog_0.csv (Errors)."""
        file_path = filedialog.askopenfilename(
            title="SPS-Fehler (plclog_0.csv) auswählen", 
            filetypes=(("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*"))
        )
        if not file_path: return
        self._start_plc_error_loading([file_path])

    def _start_plc_journey_loading(self, file_paths):
        """Startet den Lade-Thread für SPS-Journey-Logs (verwendet plclog_journey_parser)."""
        self._create_loading_window()
        thread = threading.Thread(target=self._load_and_process_plc_journey_files, args=(file_paths,), daemon=True)
        thread.start()
        self.after(100, self._check_thread, thread, "plc_journeys")

    def _start_plc_error_loading(self, file_paths):
        """Startet den Lade-Thread für SPS-Fehler-CSVs (verwendet plclog_csv_parser)."""
        self._create_loading_window()
        thread = threading.Thread(target=self._load_and_process_plc_error_files, args=(file_paths,), daemon=True)
        thread.start()
        self.after(100, self._check_thread, thread, "plc_errors")


    def _load_and_process_plc_journey_files(self, file_paths):
        """
        Lädt, parst und verarbeitet SPS-Journey-CSVs (.csv)
        Verwendet den NEUEN 'plclog_journey_parser.py'.
        """
        temp_df = pd.DataFrame()
        try:
            for file_path in file_paths:
                # Ruft den NEUEN Journey-Parser auf
                new_df = plclog_journey_parser.parse_log(
                    file_path,
                    lambda p, f: self.after(0, self._update_progress, p, f)
                )
                if not new_df.empty:
                    temp_df = pd.concat([temp_df, new_df])

            if temp_df.empty:
                print("Keine SPS-Journey-Daten (V22-Parser) gefunden.")
                self.after(0, self._populate_plc_tabs) 
                return 

            # Füge die neuen Daten zum ZIEL-DataFrame hinzu
            # --- KORREKTUR TYPO (V22) ---
            self.plc_raw_df = pd.concat([self.plc_raw_df, temp_df]).drop_duplicates().sort_values(by="Timestamp").reset_index(drop=True)
            
            # --- NEU: Konsolidiere die SPS-Journeys ---
            self.plc_journeys_df = consolidate_plc_journeys(self.plc_raw_df)
            
            self.after(0, self._populate_plc_tabs)
            
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Fehler beim Parsen (SPS-Journey)", f"Ein Fehler ist aufgetreten:\n{e}"))
            traceback.print_exc()

    def _load_and_process_plc_error_files(self, file_paths):
        """
        Lädt, parst und verarbeitet SPS-Fehler-CSVs (.csv)
        Verwendet den 'plclog_csv_parser.py'.
        """
        temp_error_df = pd.DataFrame()
        try:
            for file_path in file_paths:
                # Ruft den CSV-Parser im Modus 'errors' auf
                journeys, errors = plclog_csv_parser.parse_log(
                    file_path,
                    "errors", # Modus 'errors'
                    lambda p, f: self.after(0, self._update_progress, p, f)
                )
                if not errors.empty:
                    temp_error_df = pd.concat([temp_error_df, errors])

            if temp_error_df.empty:
                print("Keine SPS-Fehler-Daten (.csv) gefunden.")
                self.after(0, self._populate_plc_tabs) 
                return 

            # Füge die neuen Daten zum ZIEL-DataFrame hinzu
            self.plc_error_df = pd.concat([self.plc_error_df, temp_error_df]).drop_duplicates().sort_values(by="Timestamp").reset_index(drop=True)
            self.after(0, self._populate_plc_tabs)
            
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Fehler beim Parsen (SPS-Fehler-CSV)", f"Ein Fehler ist aufgetreten:\n{e}"))
            traceback.print_exc()


    def _populate_plc_tabs(self):
        """Füllt die SPS-Tabs (Journeys und Errors) basierend auf den globalen DFs."""
        
        # Hole Scanner-Zeiten für den Vergleich (nur einmal)
        scanner_times = []
        if 'Source' in self.raw_df.columns and not self.raw_df.empty:
            scanner_times = self.raw_df[self.raw_df['Source'] == 'Scanner']['Timestamp'].dropna().tolist()
        
        if not scanner_times and (not self.plc_journeys_df.empty or not self.plc_error_df.empty):
             messagebox.showwarning("Info", "Keine Scanner-Logs geladen. Zeitvergleich für SPS-Logs nicht möglich.", parent=self)

        # 1. Fülle Journey-Tab (Tab 2) - JETZT KONSOLIDIERT
        # --- KORREKTUR TYPO (V22) ---
        if not self.plc_journeys_df.empty:
            self.notebook.select(1) # Wechsle zu Tab 2
            for i in self.plc_journey_tree.get_children():
                self.plc_journey_tree.delete(i)
                
            for index, row in self.plc_journeys_df.iterrows():
                plc_time = row['Timestamp']
                
                # Finde die nächste Scanner-Zeit (dein Wunsch)
                scanner_time_str = "N/A (Keine Scanner-Logs)"
                if scanner_times and pd.notna(plc_time):
                    # Zeitstempel sind jetzt alle NAIVE, direkter Vergleich ist schnell
                    closest_time = min(scanner_times, key=lambda t: abs(t - plc_time))
                    scanner_time_str = closest_time.strftime('%Y-%m-%d %H:%M:%S')
                
                self.plc_journey_tree.insert("", "end", iid=index, values=(
                    plc_time.strftime('%Y-%m-%d %H:%M:%S'),
                    row.get('IATA', 'N/A'),
                    row.get('Klartext', 'N/A'),
                    row.get('Decision', 'N/A'),
                    scanner_time_str,
                ))

        # 2. Fülle Error-Tab (Tab 3)
        if not self.plc_error_df.empty:
            self.notebook.select(2) # Wechsle zu Tab 3
            for i in self.plc_error_tree.get_children():
                self.plc_error_tree.delete(i)
            
            for index, row in self.plc_error_df.iterrows():
                plc_time = row['Timestamp']
                        
                self.plc_error_tree.insert("", "end", values=(
                    plc_time.strftime('%Y-%m-%d %H:%M:%S') if pd.notna(plc_time) else "N/A",
                    row.get('Severity', 'N/A'),
                    row.get('Klartext', 'N/A'),
                    row.get('OriginalLog', 'N/A')
                ))
        
        # --- KORREKTUR TYPO (V22) ---
        self.status_label.config(text=f"{len(self.plc_journeys_df)} SPS-Journeys und {len(self.plc_error_df)} SPS-Fehler geladen.")

    # --- Ende der neuen PLC-Funktionen ---

    def _open_advanced_search(self):
        if self.notebook.index(self.notebook.select()) != 0:
            messagebox.showinfo("Info", "Die erweiterte Suche funktioniert nur im Tab 'Gepäck-Analyse'.", parent=self)
            return
        dialog = AdvancedSearchDialog(self); criteria = dialog.show()
        if criteria: self._perform_advanced_search(criteria)

    def _perform_advanced_search(self, criteria):
        df = self.journeys_df.copy()
        if criteria['bag_id']: df = df[df['BagID'].str.contains(criteria['bag_id'], case=False, na=False)]
        if criteria['iata']: df = df[df['IATA'].str.contains(criteria['iata'], case=False, na=False)]
        try:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            start_date_str = criteria['start_date']; end_date_str = criteria['end_date']
            if start_date_str and end_date_str:
                start_month, start_day = map(int, start_date_str.split('-')); end_month, end_day = map(int, end_date_str.split('-'))
                start_tuple = (start_month, start_day); end_tuple = (end_month, end_day)
                df_dates = df['Timestamp'].dt.strftime('%m-%d').str.split('-').apply(lambda x: (int(x[0]), int(x[1])))
                if start_tuple <= end_tuple: df = df[df_dates.between(start_tuple, end_tuple, inclusive="both")]
                else: df = df[(df_dates >= start_tuple) | (df_dates <= end_tuple)]
        except Exception as e:
            messagebox.showerror("Ungültiges Datum", f"Fehler bei der Datumsverarbeitung.\nFormat: MM-TT\nFehler: {e}"); return
        if criteria['oms_only']:
            oms_bag_ids = self.raw_df[self.raw_df['Source'] == 'OMS']['BagID'].unique()
            df = df[df['BagID'].isin(oms_bag_ids)]
        self._update_treeview(df)
        self.status_label.config(text=f"{len(df)} Einträge nach erweiterter Suche gefunden.")

    def _create_loading_window(self):
        self.loading_win = tk.Toplevel(self); self.loading_win.title("Ladevorgang"); self.loading_win.geometry("450x130"); self.loading_win.resizable(False, False); self.update_idletasks(); x = self.winfo_screenwidth() // 2 - self.loading_win.winfo_width() // 2; y = self.winfo_screenheight() // 2 - self.loading_win.winfo_height() // 2; self.loading_win.geometry(f"+{x}+{y}"); self.loading_win.transient(self); self.loading_win.grab_set(); self.loading_label = ttk.Label(self.loading_win, text="Initialisiere...", font=("Helvetica", 10)); self.loading_label.pack(pady=(15, 5), padx=10, anchor="w"); self.loading_progress_bar = ttk.Progressbar(self.loading_win, orient="horizontal", mode="determinate"); self.loading_progress_bar.pack(fill=tk.X, expand=True, padx=10); self.percent_label = ttk.Label(self.loading_win, text="0%", font=("Helvetica", 10)); self.percent_label.pack(pady=5)

    def _update_progress(self, progress, filename):
        if self.loading_win: self.loading_win.lift(); self.loading_label.config(text=f"Verarbeite: {filename}"); self.loading_progress_bar['value'] = progress; self.percent_label.config(text=f"{progress}%"); self.loading_win.update_idletasks()

    def _check_thread(self, thread, load_type):
        """Angepasst, um den Lade-Typ ('scanner' oder 'plc_...') zu kennen."""
        if thread.is_alive(): 
            self.after(100, self._check_thread, thread, load_type)
        else: 
            self.after(100, self._finalize_loading, load_type) # Übergibt den Typ

    def _load_and_process_files(self, file_paths, mode):
        """
        Lädt Scanner/OMS-Logs (TAB 1)
        NEU: Akzeptiert 'mode'
        """
        
        # Bestimme, ob nur der letzte Tag geladen werden soll
        load_last_day = (mode == "scanner_last_day")
        
        temp_raw_df = self.raw_df.copy()
        for file_path in file_paths:
            # --- NEU: Übergebe load_last_day an den Parser ---
            new_df = parse_log_file(
                file_path, 
                lambda p, f: self.after(0, self._update_progress, p, f),
                load_last_day=load_last_day
            )
            temp_raw_df = pd.concat([temp_raw_df, new_df])
        
        if temp_raw_df.empty:
            print("Keine Scanner/OMS-Daten gefunden.")
            self.journeys_df, self.raw_df = pd.DataFrame(columns=FINAL_JOURNEY_COLS), temp_raw_df # Initialisiere leer
            return

        self.raw_df = temp_raw_df.drop_duplicates().reset_index(drop=True)
        
        self.journeys_df, self.raw_df = consolidate_journeys(self.raw_df)
        
        self.after(0, lambda: self.oms_button.config(state="normal"))

    def _finalize_loading(self, load_type):
        """Entscheidet, welche UI-Aktualisierung basierend auf dem Lade-Typ stattfindet."""
        if self.loading_win: 
            self.loading_win.destroy(); self.loading_win = None
        
        if load_type == "scanner":
            self._update_gui_after_load()
        elif load_type.startswith("plc_"):
            # --- KORREKTUR DER TYPOS (V22) ---
            messagebox.showinfo("Erfolg", f"Analyse der SPS-Logs abgeschlossen.\n{len(self.plc_journeys_df)} Journeys und {len(self.plc_error_df)} Fehler insgesamt geladen.")
            self.status_label.config(text=f"{len(self.plc_journeys_df)} SPS-Journeys / {len(self.plc_error_df)} SPS-Fehler geladen.")

    def _update_gui_after_load(self):
        # Aktualisiert nur den Scanner/OMS-Tab (TAB 1)
        self._populate_filters(); self._reset_filters()
        self.status_label.config(text=f"{len(self.journeys_df)} Gepäck-Durchläufe gefunden.")
        messagebox.showinfo("Erfolg", f"Analyse (Scanner/OMS) abgeschlossen. {len(self.journeys_df)} einzigartige Gepäck-Durchläufe gefunden.")

    def _populate_filters(self):
        if not self.journeys_df.empty: 
            self.bag_id_filter['values'] = sorted(self.journeys_df['BagID'].dropna().unique())
            self.iata_filter['values'] = sorted(self.journeys_df['IATA'].dropna().unique())

    def _apply_filters(self, event=None):
        df_to_show = self.journeys_df.copy(); bag_id = self.bag_id_filter.get(); iata = self.iata_filter.get()
        if bag_id: df_to_show = df_to_show[df_to_show['BagID'] == bag_id]
        elif iata:
            matching_journeys = df_to_show[df_to_show['IATA'] == iata]
            if len(matching_journeys) > 1: self._show_iata_selection_window(matching_journeys)
            else: df_to_show = matching_journeys
        self._update_treeview(df_to_show)

    def _reset_filters(self):
        self.bag_id_filter.set(''); self.iata_filter.set(''); self._update_treeview(self.journeys_df)

    def _update_treeview(self, df):
        for i in self.tree.get_children(): self.tree.delete(i)
        
        if df.empty or not list(df.columns):
             self.tree["columns"] = []
             self.tree["show"] = "headings"
             return

        # Verwende die Spalten aus FINAL_JOURNEY_COLS (data_processor)
        cols = FINAL_JOURNEY_COLS
        
        self.tree["columns"] = cols
        self.tree["show"] = "headings"
        
        for col in cols: 
            self.tree.heading(col, text=col)
            if col == 'Device':
                self.tree.column(col, width=80, anchor='center')
            if col == 'Source':
                self.tree.column(col, width=110, anchor='center')
            if col == 'Operator':
                self.tree.column(col, width=80, anchor='center')
        
        # Zeige Daten nur für die definierten Spalten an
        df_to_show = df[cols]
        for index, row in df_to_show.iterrows(): 
            self.tree.insert("", "end", values=list(row), iid=index)

    def _on_item_double_click(self, event):
        # Funktioniert nur für Tab 1
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        
        try:
            row_index = int(item_id)
            selected_journey = self.journeys_df.loc[row_index]
            bag_id_to_find = selected_journey['BagID']
            if bag_id_to_find == 'N/A' or pd.isna(bag_id_to_find):
                messagebox.showinfo("Info", "Keine BagID für diesen Einzeleintrag vorhanden.", parent=self)
                return
            self._show_bag_history_window(bag_id_to_find)
        except Exception as e:
            print(f"Fehler bei Doppelklick: {e}")
            traceback.print_exc()

    # --- NEU: Doppelklick für Tab 2 (SPS-Journeys) ---
    def _on_plc_item_double_click(self, event):
        item_id = self.plc_journey_tree.identify_row(event.y)
        if not item_id: return
        
        try:
            row_index = int(item_id)
            # --- KORREKTUR TYPO (V22) ---
            selected_journey = self.plc_journeys_df.loc[row_index]
            iata_to_find = selected_journey['IATA']
            
            if iata_to_find == 'N/A' or pd.isna(iata_to_find):
                messagebox.showinfo("Info", "Keine IATA für diesen Einzeleintrag vorhanden.", parent=self)
                return
            
            # --- KORREKTUR TYPO (V22) ---
            # Finde alle Roh-Logs für diese IATA
            history_df = self.plc_raw_df[self.plc_raw_df['IATA'] == iata_to_find].sort_values(by="Timestamp")
            self._show_plc_history_window(iata_to_find, history_df)
            
        except Exception as e:
            print(f"Fehler bei PLC-Doppelklick: {e}")
            traceback.print_exc()

    def _extract_routing_info(self, history_df):
        info = {'iata': 'N/A', 'machine_decision': 'N/A', 'operator_decision': 'N/A', 'final_command': 'N/A', 'device': 'N/A'}
        if history_df.empty: return info
        
        # Hole IATA
        valid_iatas = history_df['IATA'][(history_df['IATA'] != 'N/A') & (history_df['IATA'] != 'NO_READ') & (pd.notna(history_df['IATA']))]
        if not valid_iatas.empty: info['iata'] = valid_iatas.iloc[0]
        
        # --- CRASH-FIX (Cannot perform 'rand_') ---
        # Korrigierte Boolean-Logik (mit Klammern)
        valid_devices_mask = (history_df['Device'] != 'N/A') & (pd.notna(history_df['Device']))
        valid_devices = history_df[valid_devices_mask]['Device'].unique()
        if len(valid_devices) > 0: info['device'] = valid_devices[0]

        # Hole Maschinen-Entscheidung
        machine_dec_df = history_df[history_df['Klartext'].str.contains("Maschinelle Entscheidung", na=False)]
        if not machine_dec_df.empty:
            match = re.search(r":\s*(.+)", machine_dec_df.iloc[-1]['Klartext'])
            if match: info['machine_decision'] = match.group(1).replace("**", "")
            
        # Hole Operator-Entscheidung
        # (Sucht jetzt nach "Finale Operator-Entscheidung" ODER "Operator-Entscheidung")
        op_dec_df = history_df[history_df['Klartext'].str.contains("Operator-Entscheidung", na=False)]
        if not op_dec_df.empty:
            last_op_klartext = op_dec_df.iloc[-1]['Klartext']
            match_op = re.search(r"von '([a-zA-Z0-9_]+)'", last_op_klartext)
            match_disp = re.search(r":\s*(.+)", last_op_klartext)
            
            op = match_op.group(1) if match_op else 'N/A'
            disp = match_disp.group(1).replace("**", "") if match_disp else 'N/A'
            
            info['operator_decision'] = f"{disp} (von {op})"
        
        # --- ÄNDERUNG: "Finale Entscheidung" priorisiert Operator ---
        if info['operator_decision'] != 'N/A' and '(von N/A)' not in info['operator_decision']:
            info['final_command'] = info['operator_decision']
        else:
            # Nur wenn kein Operator entschieden hat, suche nach dem PLC-Befehl
            final_cmd_df = history_df[history_df['Klartext'].str.contains("Finaler Befehl an Förderanlage", na=False)]
            if not final_cmd_df.empty:
                match = re.search(r"gesendet: (.+)", final_cmd_df.iloc[-1]['Klartext'])
                if match: info['final_command'] = match.group(1).replace("**", "")
            # Wenn immer noch N/A, nimm die Maschinen-Entscheidung
            elif info['machine_decision'] != 'N/A':
                 info['final_command'] = info['machine_decision']

        return info

    def _show_bag_history_window(self, bag_id):
        win = tk.Toplevel(self); win.title(f"Detail-Analyse für BagID: {bag_id}"); win.geometry("1100x800")
        
        history_df = self.raw_df[self.raw_df['BagID'] == bag_id].sort_values(by="Timestamp")
        routing_info = self._extract_routing_info(history_df)
        
        summary_frame = ttk.LabelFrame(win, text="Analyse-Ergebnis (nur für diesen Durchlauf)", padding=10); summary_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Zeile 0: IATA und GERÄT (CCT)
        ttk.Label(summary_frame, text="IATA:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(summary_frame, text=routing_info['iata']).grid(row=0, column=1, sticky="w")
        ttk.Label(summary_frame, text="Gerät:", font=("Helvetica", 10, "bold")).grid(row=0, column=2, sticky="w", padx=(20, 5))
        ttk.Label(summary_frame, text=routing_info['device']).grid(row=0, column=3, sticky="w")

        # Zeile 1: Maschinen-Entscheid
        ttk.Label(summary_frame, text="Maschinen-Entscheid:", font=("Helvetica", 10, "bold")).grid(row=1, column=0, sticky="w")
        ttk.Label(summary_frame, text=routing_info['machine_decision']).grid(row=1, column=1, sticky="w")
        
        # Zeile 2: Operator-Entscheid
        ttk.Label(summary_frame, text="Operator-Entscheid:", font=("Helvetica", 10, "bold")).grid(row=2, column=0, sticky="w")
        ttk.Label(summary_frame, text=routing_info['operator_decision']).grid(row=2, column=1, sticky="w")
        
        # Zeile 3: Finale Entscheidung
        ttk.Label(summary_frame, text="Finale Entscheidung:", font=("Helvetica", 10, "bold")).grid(row=3, column=0, sticky="w")
        ttk.Label(summary_frame, text=routing_info['final_command']).grid(row=3, column=1, sticky="w")
        
        
        notebook = ttk.Notebook(win); notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        tab1 = ttk.Frame(notebook); notebook.add(tab1, text="Klartext-Analyse (BagID-bezogen)"); text1 = tk.Text(tab1, wrap=tk.WORD, font=("Courier New", 10)); text1.pack(fill=tk.BOTH, expand=True)
        tab2 = ttk.Frame(notebook); notebook.add(tab2, text="Scanner-Log Auszug (BagID-bezogen)"); text2 = tk.Text(tab2, wrap=tk.WORD, font=("Courier New", 9)); text2.pack(fill=tk.BOTH, expand=True)
        tab3 = ttk.Frame(notebook); notebook.add(tab3, text="OMS-Log Auszug (BagID-bezogen)"); text3 = tk.Text(tab3, wrap=tk.WORD, font=("Courier New", 9)); text3.pack(fill=tk.BOTH, expand=True)
        
        export_content = self._build_export_content(history_df, bag_id, routing_info)
        
        if not history_df.empty:
            # --- FIX FÜR DOPPELTE EINTRÄGE ---
            history_df_no_duplicates = history_df.drop_duplicates(subset=['Klartext'])
            
            header = f"Chronologische Analyse für BagID: {bag_id} (Wanne: {routing_info['iata']}, Gerät: {routing_info['device']})\n"; text1.insert(tk.END, header + "=" * len(header) + "\n\n")
            for _, row in history_df_no_duplicates.iterrows(): 
                # --- FIX: Zeige Original-Log-Zeit (Kein UTC) ---
                ts_str = row['Timestamp'].strftime('%H:%M:%S.%f')[:-3]
                full_line = f"[{ts_str}] {row['Klartext']}\n"; text1.insert(tk.END, full_line.replace("**", ""))
            
            scanner_logs_df = history_df[history_df['Source'] == 'Scanner']
            if not scanner_logs_df.empty:
                for _, row in scanner_logs_df.iterrows(): text2.insert(tk.END, row['OriginalLog'] + "\n")
            else: text2.insert(tk.END, f"Keine Scanner-Einträge für BagID {bag_id} gefunden.")
            
            oms_logs_df = history_df[history_df['Source'] == 'OMS']
            if not oms_logs_df.empty:
                for _, row in oms_logs_df.iterrows(): 
                    ts_str = row['Timestamp'].strftime('%H:%M:%S.%f')[:-3]
                    text3.insert(tk.END, f"[{ts_str}] {row['OriginalLog']}\n")
            else: text3.insert(tk.END, f"Keine OMS-Einträge für BagID {bag_id} gefunden.")
        else:
            msg = f"Keine Detail-Einträge für BagID {bag_id} gefunden."
            for txt in [text1, text2, text3]: txt.insert(tk.END, msg)
            
        for txt in [text1, text2, text3]: txt.config(state=tk.DISABLED)
        ttk.Button(win, text="Analyse speichern...", command=lambda: self._save_analysis(bag_id, routing_info['iata'], export_content)).pack(pady=10)

    # --- NEU: Detail-Fenster für SPS-Journeys (Tab 2) ---
    def _show_plc_history_window(self, iata, history_df):
        win = tk.Toplevel(self); win.title(f"SPS-Detail-Analyse für IATA: {iata}"); win.geometry("1100x700")
        
        summary_frame = ttk.LabelFrame(win, text="SPS-Vorgang (nur PlcLog.csv)", padding=10); summary_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Finde die finale Entscheidung (falls vorhanden)
        final_decision = "N/A"
        final_dec_df = history_df[history_df['Klartext'].str.contains("Finale Entscheidung", na=False)]
        if not final_dec_df.empty:
            match = re.search(r"Finale Entscheidung.*:\s*(\S+)", final_dec_df.iloc[-1]['Klartext'])
            if match: final_decision = match.group(1)

        ttk.Label(summary_frame, text="IATA:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(summary_frame, text=iata).grid(row=0, column=1, sticky="w")
        ttk.Label(summary_frame, text="Finale Entscheidung:", font=("Helvetica", 10, "bold")).grid(row=0, column=2, sticky="w", padx=(20, 5))
        ttk.Label(summary_frame, text=final_decision).grid(row=0, column=3, sticky="w")

        notebook = ttk.Notebook(win); notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        tab1 = ttk.Frame(notebook); notebook.add(tab1, text="Klartext-Analyse (IATA-bezogen)"); text1 = tk.Text(tab1, wrap=tk.WORD, font=("Courier New", 10)); text1.pack(fill=tk.BOTH, expand=True)
        tab2 = ttk.Frame(notebook); notebook.add(tab2, text="Original-Log Auszug (IATA-bezogen)"); text2 = tk.Text(tab2, wrap=tk.WORD, font=("Courier New", 9)); text2.pack(fill=tk.BOTH, expand=True)

        if not history_df.empty:
            history_df_no_duplicates = history_df.drop_duplicates(subset=['Klartext'])
            
            header = f"Chronologische SPS-Analyse für IATA: {iata}\n"; text1.insert(tk.END, header + "=" * len(header) + "\n\n")
            for _, row in history_df_no_duplicates.iterrows(): 
                ts_str = row['Timestamp'].strftime('%H:%M:%S') # Zeit ohne Millisekunden
                full_line = f"[{ts_str}] {row['Klartext']}\n"; text1.insert(tk.END, full_line.replace("**", ""))
            
            for _, row in history_df.iterrows(): 
                text2.insert(tk.END, row['OriginalLog'] + "\n")
        else:
            msg = f"Keine Detail-Einträge für IATA {iata} gefunden."
            text1.insert(tk.END, msg)
            text2.insert(tk.END, msg)
            
        text1.config(state=tk.DISABLED)
        text2.config(state=tk.DISABLED)

    def _build_export_content(self, history_df, bag_id, routing_info):
        if history_df.empty: return f"Keine Detail-Einträge für BagID {bag_id} gefunden."
        
        content_parts = [
            f"ANALYSE-REPORT FÜR BAGID {bag_id} (WANNE: {routing_info['iata']}, GERÄT: {routing_info['device']})", 
            f"Erstellt am: {datetime.now().strftime('%d.%m.%Y um %H:%M:%S Uhr')}", "="*60, 
            "\n--- ROUTING-ANALYSE ---", 
            f"IATA: {routing_info['iata']}", 
            f"Gerät: {routing_info['device']}",
            f"Maschinen-Entscheid: {routing_info['machine_decision']}", 
            f"Operator-Entscheid: {routing_info['operator_decision']}", 
            f"Finale Entscheidung: {routing_info['final_command']}\n", 
            "--- KLARTEXT-ANALYSE (BAGID-BEZOGEN) ---"
        ]
        
        # --- FIX FÜR DOPPELTE EINTRÄGE ---
        history_df_no_duplicates = history_df.drop_duplicates(subset=['Klartext'])
        
        for _, row in history_df_no_duplicates.iterrows(): 
            ts_str = row['Timestamp'].strftime('%H:%M:%S.%f')[:-3] # Kein UTC
            content_parts.append(f"[{ts_str}] {row['Klartext'].replace('**', '')}")
        
        content_parts.append("\n--- SCANNER-LOG AUSZUG (BAGID-BEZOGEN) ---")
        scanner_logs = history_df[history_df['Source'] == 'Scanner']['OriginalLog']
        if not scanner_logs.empty: content_parts.extend(scanner_logs.tolist())
        else: content_parts.append("Keine Scanner-Logs für diesen Durchlauf gefunden.")
        
        content_parts.append("\n--- OMS-LOG AUSZUG (BAGID-BEZOGEN) ---")
        oms_logs_df = history_df[history_df['Source'] == 'OMS']
        if not oms_logs_df.empty:
            for _, row in oms_logs_df.iterrows(): 
                ts_str = row['Timestamp'].strftime('%H:%M:%S.%f')[:-3] # Kein UTC
                content_parts.append(f"[{ts_str}] {row['OriginalLog']}")
        else: content_parts.append("Keine OMS-Logs für diesen Durchlauf gefunden.")
        
        return "\n".join(content_parts)

    def _save_analysis(self, bag_id, iata, content):
        file_path = filedialog.asksaveasfilename(initialfile=f"Analyse_{bag_id}_{iata}", defaultextension=".txt", filetypes=[("Textdateien", "*.txt"), ("PDF-Dokumente", "*.pdf"), ("Alle Dateien", "*.*")])
        if not file_path: return
        if file_path.lower().endswith(".pdf"): self._export_to_pdf(file_path, content)
        else: self._export_to_txt(file_path, content)

    def _export_to_txt(self, path, content):
        try:
            with open(path, 'w', encoding='utf-8') as f: f.write(content)
            messagebox.showinfo("Erfolg", f"Analyse erfolgreich gespeichert unter:\n{path}")
        except Exception as e: messagebox.showerror("Fehler", f"Datei konnte nicht gespeichert werden:\n{e}")

    def _export_to_pdf(self, path, content):
        try:
            doc = SimpleDocTemplate(path, pagesize=landscape(letter))
            styles = getSampleStyleSheet()
            code_style = styles['Code']; code_style.alignment = TA_LEFT
            content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            content_with_breaks = content.replace('\n', '<br/>\n')
            story = [Paragraph(content_with_breaks, code_style)]
            doc.build(story)
            messagebox.showinfo("Erfolg", f"PDF erfolgreich gespeichert unter:\n{path}")
        except Exception as e:
            messagebox.showerror("Fehler beim PDF-Export", f"PDF konnte nicht erstellt werden:\n{e}")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        root = tk.Tk()
        app = GateViewApp(root)
        root.mainloop()
    except Exception as e:
        with open("gateview_crash_report.log", "w", encoding='utf-8') as f:
            f.write("Ein kritischer Fehler ist in gateview_app.py aufgetreten:\n\n")
            f.write(traceback.format_exc())