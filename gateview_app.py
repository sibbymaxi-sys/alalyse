# gateview_app.py
print("--- [V23-FIX-V8] gateview_app.py wird geladen (OMS-Doppelklick-Fix) ... ---")

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
import pytz # Import für Zeitzonen-Konvertierung

try:
    import sv_ttk
    from tkcalendar import DateEntry
    
    from log_parser import parse_log_file         # Für Scanner (.log)
    from oms_log_parser import parse_oms_log      # NEU: Für OMS (.log)
    
    import plclog_journey_parser                  
    import plclog_csv_parser                      
    
    from data_processor import (
        consolidate_scanner_journeys, 
        consolidate_oms_journeys,
        consolidate_plc_journeys, 
        FINAL_JOURNEY_COLS_SCANNER, # Für Tab 1
        FINAL_JOURNEY_COLS_OMS      # Für Tab 4
    )
    
    from oms_report_generator import generate_oms_report
    
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
        
        # --- V13: Getrennte Datenhaltung ---
        self.scanner_raw_df = pd.DataFrame()
        self.scanner_journeys_df = pd.DataFrame()
        self.oms_raw_df = pd.DataFrame()
        self.oms_journeys_df = pd.DataFrame()
        self.plc_raw_df = pd.DataFrame() 
        self.plc_journeys_df = pd.DataFrame() 
        self.plc_error_df = pd.DataFrame()
        
        self.loading_win = None
        self._setup_ui()

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding="10"); main_frame.pack(fill=tk.BOTH, expand=True)
        
        button_frame = ttk.Frame(main_frame); button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="1a. Scanner-Logs laden", command=lambda: self._load_from_dialog(mode="scanner_full")).pack(side=tk.LEFT, padx=(5,0))
        ttk.Button(button_frame, text="1b. Scanner (Letzter Tag)", command=lambda: self._load_from_dialog(mode="scanner_last_day"), style='Accent.TButton').pack(side=tk.LEFT, padx=(5,5))
        self.oms_button = ttk.Button(button_frame, text="2. OMS-Logs laden", command=lambda: self._load_from_dialog(mode="oms"), state="normal"); self.oms_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="3. SPS-Journeys laden (CSV)", command=self._load_plc_journeys_from_dialog, style='Accent.TButton').pack(side=tk.LEFT, padx=(15, 5))
        ttk.Button(button_frame, text="4. SPS-Fehler laden (CSV)", command=self._load_plc_errors_from_dialog, style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="System-Analyse", command=self._launch_system_analyzer).pack(side=tk.LEFT, padx=(15, 5))
        self.search_button = ttk.Button(button_frame, text="Erweiterte Suche", command=self._open_advanced_search); self.search_button.pack(side=tk.LEFT, padx=5)
        
        filter_frame = ttk.Frame(main_frame, padding=(0, 5)); filter_frame.pack(fill=tk.X, pady=(10,0))
        ttk.Label(filter_frame, text="Filter (nur Gepäck-Analyse):").pack(side=tk.LEFT, padx=(0, 5)); ttk.Label(filter_frame, text="BagID:").pack(side=tk.LEFT, padx=(10, 5)); self.bag_id_filter = ttk.Combobox(filter_frame, width=15); self.bag_id_filter.pack(side=tk.LEFT); ttk.Label(filter_frame, text="IATA:").pack(side=tk.LEFT, padx=(10, 5)); self.iata_filter = ttk.Combobox(filter_frame, width=10); self.iata_filter.pack(side=tk.LEFT); self.iata_filter.bind("<<ComboboxSelected>>", self._apply_filters); ttk.Button(filter_frame, text="Anwenden", command=self._apply_filters).pack(side=tk.LEFT, padx=5); ttk.Button(filter_frame, text="Zurücksetzen", command=self._reset_filters).pack(side=tk.LEFT, padx=5)
        
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(5,0))
        
        # --- TAB 1: Gepäck-Analyse (Scanner) ---
        tab1_frame = ttk.Frame(self.notebook, padding=(0, 5))
        self.notebook.add(tab1_frame, text="Gepäck-Analyse (Scanner-Log)")
        tree_frame = ttk.Frame(tab1_frame); tree_frame.pack(fill=tk.BOTH, expand=True, pady=(5,0))
        self.tree = ttk.Treeview(tree_frame); scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set); scrollbar.pack(side=tk.RIGHT, fill=tk.Y); self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); self.tree.bind("<Double-1>", self._on_item_double_click)
        
        self.tree.tag_configure('EDS_MISMATCH', background='#E53935', foreground='white') # Leuchtendes Rot

        # --- TAB 2: SPS-Journeys (aus .csv) ---
        tab2_frame = ttk.Frame(self.notebook, padding=(0, 5))
        self.notebook.add(tab2_frame, text="SPS-Journeys (PlcLog.csv)")
        plc_journey_tree_frame = ttk.Frame(tab2_frame); plc_journey_tree_frame.pack(fill=tk.BOTH, expand=True, pady=(5,0))
        plc_journey_cols = ("plc_time", "iata", "klartext", "decision", "scanner_time", "JourneyID")
        self.plc_journey_tree = ttk.Treeview(plc_journey_tree_frame, columns=plc_journey_cols, show="headings")
        self.plc_journey_tree.heading("plc_time", text="SPS Zeit"); self.plc_journey_tree.column("plc_time", width=170)
        self.plc_journey_tree.heading("iata", text="IATA"); self.plc_journey_tree.column("iata", width=100)
        self.plc_journey_tree.heading("klartext", text="Beschreibung"); self.plc_journey_tree.column("klartext", width=300)
        self.plc_journey_tree.heading("decision", text="Finale Entscheidung"); self.plc_journey_tree.column("decision", width=150)
        self.plc_journey_tree.heading("scanner_time", text="Nächste Scanner-Zeit"); self.plc_journey_tree.column("scanner_time", width=170)
        self.plc_journey_tree.heading("JourneyID", text="ID"); 
        self.plc_journey_tree.column("JourneyID", width=0, stretch=False) 
        plc_journey_scrollbar = ttk.Scrollbar(plc_journey_tree_frame, orient="vertical", command=self.plc_journey_tree.yview); self.plc_journey_tree.configure(yscrollcommand=plc_journey_scrollbar.set); plc_journey_scrollbar.pack(side=tk.RIGHT, fill=tk.Y); self.plc_journey_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
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
        
        # --- TAB 4: OMS-Analyse ---
        tab4_frame = ttk.Frame(self.notebook, padding=(0, 5))
        self.notebook.add(tab4_frame, text="OMS-Analyse (OMS.log)")
        
        oms_button_frame = ttk.Frame(tab4_frame); 
        oms_button_frame.pack(fill=tk.X, pady=(0, 5))
        self.oms_report_button = ttk.Button(oms_button_frame, text="OMS-Report speichern...", command=self._save_oms_report, state="disabled")
        self.oms_report_button.pack(side=tk.LEFT)
        
        oms_tree_frame = ttk.Frame(tab4_frame); 
        oms_tree_frame.pack(fill=tk.BOTH, expand=True, pady=(5,0))
        
        # --- KORREKTUR (V8): Spalten (inkl. JourneyID) ---
        oms_cols = FINAL_JOURNEY_COLS_OMS # ['Timestamp', 'IATA', 'EDS', 'Operator', 'Final', 'JourneyID']
        self.oms_tree = ttk.Treeview(oms_tree_frame, columns=oms_cols, show="headings")
        for col in oms_cols:
            self.oms_tree.heading(col, text=col)
            if col == 'Timestamp': self.oms_tree.column(col, width=170)
            # --- NEU (V8): JourneyID verstecken ---
            elif col == 'JourneyID': self.oms_tree.column(col, width=0, stretch=False)
            else: self.oms_tree.column(col, width=100, anchor='center')

        oms_scrollbar = ttk.Scrollbar(oms_tree_frame, orient="vertical", command=self.oms_tree.yview); self.oms_tree.configure(yscrollcommand=oms_scrollbar.set); oms_scrollbar.pack(side=tk.RIGHT, fill=tk.Y); self.oms_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.oms_tree.bind("<Double-1>", self._on_oms_item_double_click)
        
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
            pass 
            
        if "SPS-Journeys" in profile_name: 
             self.after(0, self._start_plc_journey_loading, all_downloaded_files)
        elif "SPS-Fehler" in profile_name: 
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
        messagebox.showinfo("Download Abgeschlossen", f"{len(downloaded_files)} Datei(en) heruntergeladen.\nAnalyse wird gestartet.", parent=self)
        
        if mode == "oms":
            self.oms_raw_df = pd.DataFrame()
            self.oms_journeys_df = pd.DataFrame()
        else: # scanner
            self.scanner_raw_df = pd.DataFrame()
            self.scanner_journeys_df = pd.DataFrame()
            
        self._start_loading_process(downloaded_files, mode)

    def _start_loading_process(self, file_paths, mode):
        self._create_loading_window()
        
        load_type = "oms" if mode == "oms" else "scanner"
        
        thread = threading.Thread(target=self._load_and_process_files, args=(file_paths, mode), daemon=True); thread.start()
        self.after(100, self._check_thread, thread, load_type) 

    def _load_from_dialog(self, mode):
        config = cfg.load_config()
        last_dir = config.get("last_gateview_dir", os.getcwd())
        
        title = "OMS-Log (OMS.log) auswählen" if mode == "oms" else "Scanner-Log (scanner_bag.log) auswählen"
        file_types = (("Logdateien", "*.log*"), ("Alle Dateien", "*.*")) # *.log*
            
        # --- KORREKTUR (V7): Erlaube Mehrfachauswahl ---
        file_paths = filedialog.askopenfilenames(title=title, initialdir=last_dir, filetypes=file_types)
        if not file_paths: # file_paths ist jetzt ein Tuple
            return
        
        config["last_gateview_dir"] = os.path.dirname(file_paths[0]); cfg.save_config(config) # Nimm das Verzeichnis der ersten Datei
        # --- ENDE KORREKTUR ---
        
        if mode == "oms":
            self.oms_raw_df = pd.DataFrame()
            self.oms_journeys_df = pd.DataFrame()
        else: # scanner_full or scanner_last_day
            self.scanner_raw_df = pd.DataFrame() 
            self.scanner_journeys_df = pd.DataFrame()
            
        self._start_loading_process(file_paths, mode) # Übergebe das Tuple

    # --- SPS-Funktionen (Tab 2 & 3) - Unverändert ---
    def _load_plc_journeys_from_dialog(self):
        file_path = filedialog.askopenfilename(
            title="SPS-Journeys (PlcLog.csv) auswählen", 
            filetypes=(("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*"))
        )
        if not file_path: return
        self._start_plc_journey_loading([file_path])

    def _load_plc_errors_from_dialog(self):
        file_path = filedialog.askopenfilename(
            title="SPS-Fehler (plclog_0.csv) auswählen", 
            filetypes=(("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*"))
        )
        if not file_path: return
        self._start_plc_error_loading([file_path])

    def _start_plc_journey_loading(self, file_paths):
        self._create_loading_window()
        thread = threading.Thread(target=self._load_and_process_plc_journey_files, args=(file_paths,), daemon=True)
        thread.start()
        self.after(100, self._check_thread, thread, "plc_journeys")

    def _start_plc_error_loading(self, file_paths):
        self._create_loading_window()
        thread = threading.Thread(target=self._load_and_process_plc_error_files, args=(file_paths,), daemon=True)
        thread.start()
        self.after(100, self._check_thread, thread, "plc_errors")

    def _load_and_process_plc_journey_files(self, file_paths):
        temp_df = pd.DataFrame()
        try:
            for file_path in file_paths:
                new_df = plclog_journey_parser.parse_log(
                    file_path,
                    lambda p, f: self.after(0, self._update_progress, p, f)
                )
                if not new_df.empty:
                    temp_df = pd.concat([temp_df, new_df])

            if temp_df.empty:
                print("Keine SPS-Journey-Daten (V23-Parser) gefunden.")
                self.after(0, self._populate_plc_tabs) 
                return 
            
            raw_data_with_iata = pd.concat([self.plc_raw_df, temp_df]).drop_duplicates().sort_values(by="Timestamp").reset_index(drop=True)
            
            self.plc_journeys_df, self.plc_raw_df = consolidate_plc_journeys(raw_data_with_iata)
            
            self.after(0, self._populate_plc_tabs)
            
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Fehler beim Parsen (SPS-Journey)", f"Ein Fehler ist aufgetreten:\n{e}"))
            traceback.print_exc()

    def _load_and_process_plc_error_files(self, file_paths):
        temp_error_df = pd.DataFrame()
        try:
            for file_path in file_paths:
                journeys, errors = plclog_csv_parser.parse_log(
                    file_path,
                    "errors", 
                    lambda p, f: self.after(0, self._update_progress, p, f)
                )
                if not errors.empty:
                    temp_error_df = pd.concat([temp_error_df, errors])

            if temp_error_df.empty:
                print("Keine SPS-Fehler-Daten (.csv) gefunden.")
                self.after(0, self._populate_plc_tabs) 
                return 

            self.plc_error_df = pd.concat([self.plc_error_df, temp_error_df]).drop_duplicates().sort_values(by="Timestamp").reset_index(drop=True)
            self.after(0, self._populate_plc_tabs)
            
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Fehler beim Parsen (SPS-Fehler-CSV)", f"Ein Fehler ist aufgetreten:\n{e}"))
            traceback.print_exc()

    def _populate_plc_tabs(self):
        scanner_times = []
        if 'Timestamp' in self.scanner_raw_df.columns and not self.scanner_raw_df.empty:
            scanner_times = self.scanner_raw_df['Timestamp'].dropna().tolist()
        
        if not scanner_times and (not self.plc_journeys_df.empty or not self.plc_error_df.empty):
             messagebox.showwarning("Info", "Keine Scanner-Logs geladen. Zeitvergleich für SPS-Logs nicht möglich.", parent=self)

        if not self.plc_journeys_df.empty:
            self.notebook.select(1) 
            for i in self.plc_journey_tree.get_children():
                self.plc_journey_tree.delete(i)
                
            for index, row in self.plc_journeys_df.iterrows():
                plc_time = row['Timestamp']
                
                scanner_time_str = "N/A (Keine Scanner-Logs)"
                if scanner_times and pd.notna(plc_time):
                    if plc_time.tzinfo is None:
                        try:
                            local_tz = pytz.timezone('Europe/Berlin')
                            plc_time_aware = local_tz.localize(plc_time, is_dst=None)
                            plc_time_utc = plc_time_aware.astimezone(pytz.utc)
                        except Exception:
                            plc_time_utc = plc_time 
                    else:
                        plc_time_utc = plc_time.astimezone(pytz.utc)

                    closest_time = min(scanner_times, key=lambda t: abs(t - plc_time_utc))
                    scanner_time_str = closest_time.strftime('%Y-%m-%d %H:%M:%S')
                
                self.plc_journey_tree.insert("", "end", iid=index, values=(
                    plc_time.strftime('%Y-%m-%d %H:%M:%S'),
                    row.get('IATA', 'N/A'),
                    row.get('Klartext', 'N/A'),
                    row.get('Decision', 'N/A'),
                    scanner_time_str,
                    row.get('JourneyID', -1) 
                ))

        if not self.plc_error_df.empty:
            self.notebook.select(2) 
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
        
        self.status_label.config(text=f"{len(self.plc_journeys_df)} SPS-Journeys und {len(self.plc_error_df)} SPS-Fehler geladen.")
    # --- ENDE SPS-Funktionen ---

    def _open_advanced_search(self):
        if self.notebook.index(self.notebook.select()) != 0:
            messagebox.showinfo("Info", "Die erweiterte Suche funktioniert nur im Tab 'Gepäck-Analyse (Scanner-Log)'.", parent=self)
            return
        dialog = AdvancedSearchDialog(self); criteria = dialog.show()
        if criteria: self._perform_advanced_search(criteria)

    def _perform_advanced_search(self, criteria):
        df = self.scanner_journeys_df.copy()
        if criteria['bag_id']: df = df[df['BagID'].str.contains(criteria['bag_id'], case=False, na=False)]
        if criteria['iata']: df = df[df['IATA'].str.contains(criteria['iata'], case=False, na=False)]
        try:
            df['Timestamp_UTC'] = pd.to_datetime(df['Timestamp']).dt.tz_convert('UTC')
            start_date_str = criteria['start_date']; end_date_str = criteria['end_date']
            
            if start_date_str and end_date_str:
                start_month, start_day = map(int, start_date_str.split('-'))
                end_month, end_day = map(int, end_date_str.split('-'))
                start_tuple = (start_month, start_day); end_tuple = (end_month, end_day)
                df_dates = df['Timestamp_UTC'].dt.strftime('%m-%d').str.split('-').apply(lambda x: (int(x[0]), int(x[1])))

                if start_tuple <= end_tuple:
                    df = df[df_dates.between(start_tuple, end_tuple, inclusive="both")]
                else: 
                    df = df[(df_dates >= start_tuple) | (df_dates <= end_tuple)]
        except Exception as e:
            messagebox.showerror("Ungültiges Datum", f"Fehler bei der Datumsverarbeitung.\nFormat: MM-TT\nFehler: {e}"); return
        
        self._update_treeview(df)
        self.status_label.config(text=f"{len(df)} Einträge nach erweiterter Suche gefunden.")

    def _create_loading_window(self):
        self.loading_win = tk.Toplevel(self); self.loading_win.title("Ladevorgang"); self.loading_win.geometry("450x130"); self.loading_win.resizable(False, False); self.update_idletasks(); x = self.winfo_screenwidth() // 2 - self.loading_win.winfo_width() // 2; y = self.winfo_screenheight() // 2 - self.loading_win.winfo_height() // 2; self.loading_win.geometry(f"+{x}+{y}"); self.loading_win.transient(self); self.loading_win.grab_set(); self.loading_label = ttk.Label(self.loading_win, text="Initialisiere...", font=("Helvetica", 10)); self.loading_label.pack(pady=(15, 5), padx=10, anchor="w"); self.loading_progress_bar = ttk.Progressbar(self.loading_win, orient="horizontal", mode="determinate"); self.loading_progress_bar.pack(fill=tk.X, expand=True, padx=10); self.percent_label = ttk.Label(self.loading_win, text="0%", font=("Helvetica", 10)); self.percent_label.pack(pady=5)

    def _update_progress(self, progress, filename):
        if self.loading_win: self.loading_win.lift(); self.loading_label.config(text=f"Verarbeite: {filename}"); self.loading_progress_bar['value'] = progress; self.percent_label.config(text=f"{progress}%"); self.loading_win.update_idletasks()

    def _update_loading_text(self, text):
        if self.loading_win:
            self.loading_label.config(text=text)
            self.loading_win.update_idletasks()

    def _check_thread(self, thread, load_type):
        if thread.is_alive(): 
            self.after(100, self._check_thread, thread, load_type)
        else: 
            self.after(100, self._finalize_loading, load_type) 

    def _load_and_process_files(self, file_paths, mode):
        load_last_day = (mode == "scanner_last_day")
        
        if mode == "oms":
            # --- OMS-Ladevorgang (Tab 4) ---
            temp_raw_df = pd.DataFrame()
            for file_path in file_paths:
                new_df = parse_oms_log(
                    file_path, 
                    lambda p, f: self.after(0, self._update_progress, p, f)
                )
                temp_raw_df = pd.concat([temp_raw_df, new_df])
            
            if temp_raw_df.empty:
                print("Keine OMS-Daten gefunden.")
                return

            self.after(0, self._update_loading_text, "Daten werden konsolidiert (kann dauern)...")
            temp_raw_df['Timestamp'] = pd.to_datetime(temp_raw_df['Timestamp'], utc=True)
            self.oms_raw_df = temp_raw_df.drop_duplicates().reset_index(drop=True)
            
            if not self.oms_raw_df.empty:
                self.oms_journeys_df, self.oms_raw_df = consolidate_oms_journeys(self.oms_raw_df)

        else:
            # --- SCANNER-Ladevorgang (Tab 1) ---
            temp_raw_df = pd.DataFrame()
            for file_path in file_paths:
                new_df = parse_log_file(
                    file_path, 
                    lambda p, f: self.after(0, self._update_progress, p, f),
                    load_last_day=load_last_day
                )
                temp_raw_df = pd.concat([temp_raw_df, new_df])
            
            if temp_raw_df.empty:
                print("Keine Scanner-Daten gefunden.")
                return

            self.after(0, self._update_loading_text, "Daten werden konsolidiert (kann dauern)...")
            temp_raw_df['Timestamp'] = pd.to_datetime(temp_raw_df['Timestamp'], utc=True)
            self.scanner_raw_df = temp_raw_df.drop_duplicates().reset_index(drop=True)
            
            if not self.scanner_raw_df.empty:
                self.scanner_journeys_df, self.scanner_raw_df = consolidate_scanner_journeys(self.scanner_raw_df)

    def _finalize_loading(self, load_type):
        if self.loading_win: 
            self.loading_win.destroy(); self.loading_win = None
        
        if load_type == "scanner":
            self._update_gui_after_load() # Füllt Tab 1
        elif load_type == "oms":
            self._populate_oms_tab() # Füllt Tab 4
        elif load_type.startswith("plc_"):
            self._populate_plc_tabs() # Füllt Tab 2 & 3
            
    def _update_gui_after_load(self):
        # Aktualisiert nur den Scanner-Tab (TAB 1)
        self._populate_filters(); self._reset_filters()
        self.status_label.config(text=f"{len(self.scanner_journeys_df)} Scanner-Durchläufe gefunden.")
        messagebox.showinfo("Erfolg", f"Analyse (Scanner) abgeschlossen. {len(self.scanner_journeys_df)} einzigartige Scanner-Durchläufe gefunden.")

    def _populate_oms_tab(self):
        self.notebook.select(3) # Wechsle zu Tab 4
        for i in self.oms_tree.get_children():
            self.oms_tree.delete(i)
        
        df = self.oms_journeys_df
        if df.empty:
            messagebox.showwarning("Keine Daten", "Keine OMS-Journeys gefunden (oder keine IATAs in OMS.log).", parent=self)
            self.oms_report_button.config(state="disabled")
            return

        for index, row in df.iterrows():
            try:
                local_tz = pytz.timezone('Europe/Berlin')
                ts_utc = pd.to_datetime(row['Timestamp']).tz_convert('UTC')
                ts_local = ts_utc.astimezone(local_tz)
                ts_str = ts_local.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                ts_str = str(row['Timestamp'])
                
            values_list = list(row)
            values_list[0] = ts_str
            
            # --- KORREKTUR (V8): Übergebe iid=index ---
            self.oms_tree.insert("", "end", values=values_list, iid=index)
            
        self.oms_report_button.config(state="normal") # Aktiviere Report-Button
        self.status_label.config(text=f"Analyse (OMS) abgeschlossen. {len(df)} OMS-Durchläufe gefunden.")
        messagebox.showinfo("Erfolg", f"Analyse (OMS) abgeschlossen. {len(df)} einzigartige OMS-Durchläufe (nach IATA) gefunden.")

    def _populate_filters(self):
        if not self.scanner_journeys_df.empty: 
            self.bag_id_filter['values'] = sorted(self.scanner_journeys_df['BagID'].dropna().unique())
            self.iata_filter['values'] = sorted(self.scanner_journeys_df['IATA'].dropna().unique())

    def _apply_filters(self, event=None):
        df_to_show = self.scanner_journeys_df.copy(); bag_id = self.bag_id_filter.get(); iata = self.iata_filter.get()
        if bag_id: df_to_show = df_to_show[df_to_show['BagID'] == bag_id]
        elif iata:
            df_to_show = df_to_show[df_to_show['IATA'] == iata]
        self._update_treeview(df_to_show)

    def _reset_filters(self):
        self.bag_id_filter.set(''); self.iata_filter.set(''); self._update_treeview(self.scanner_journeys_df)

    def _update_treeview(self, df):
        # Füllt Tab 1 (Scanner)
        for i in self.tree.get_children(): self.tree.delete(i)
        
        if df.empty or not list(df.columns):
             self.tree["columns"] = []
             self.tree["show"] = "headings"
             return

        cols = FINAL_JOURNEY_COLS_SCANNER
        
        self.tree["columns"] = cols
        self.tree["show"] = "headings"
        
        for col in cols: 
            self.tree.heading(col, text=col)
            if col == 'Timestamp': self.tree.column(col, width=160)
            elif col == 'BagID': self.tree.column(col, width=110)
            # --- NEU (V6): 'OperatorName' verstecken ---
            elif col == 'OperatorName': self.tree.column(col, width=0, stretch=False)
            else: self.tree.column(col, width=80, anchor='center')
        
        df_to_show = df[cols]
        for index, row in df_to_show.iterrows(): 
            try:
                local_tz = pytz.timezone('Europe/Berlin')
                ts_utc = pd.to_datetime(row['Timestamp']).tz_convert('UTC')
                ts_local = ts_utc.astimezone(local_tz)
                ts_str = ts_local.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                ts_str = str(row['Timestamp']) 
                
            values_list = list(row)
            values_list[0] = ts_str
            
            # --- NEU (V6): Rote-Markierung-Logik ---
            tags_to_apply = ()
            try:
                eds_val = row.get('EDS', 'N/A')
                op_name = row.get('OperatorName', 'N/A') # Holt den internen Namen
                
                # Wenn EDS ALARM ist UND ein Operator (der NICHT 3 oder 4 ist) die Entscheidung getroffen hat
                if eds_val == 'ALARM' and (op_name not in ['operator3', 'operator4', 'N/A']):
                    tags_to_apply = ('EDS_MISMATCH',)
            except Exception as e:
                print(f"Fehler bei Tag-Logik: {e}")
            
            self.tree.insert("", "end", values=values_list, iid=index, tags=tags_to_apply)
            # --- ENDE NEU ---

    def _on_item_double_click(self, event):
        # Doppelklick für Tab 1 (Scanner)
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        
        try:
            row_index = int(item_id)
            selected_journey = self.scanner_journeys_df.loc[row_index]
            
            bag_id_to_find = selected_journey['BagID']
            iata_to_find = selected_journey['IATA']
            
            if (bag_id_to_find == 'N/A' or pd.isna(bag_id_to_find)):
                 messagebox.showinfo("Info", "Keine BagID für diesen Eintrag vorhanden.", parent=self)
                 return
            
            # KORREKTUR (V14): Filtert Rohdaten nach BagID UND IATA
            self._show_bag_history_window(bag_id_to_find, iata_to_find)
            
        except Exception as e:
            print(f"Fehler bei Doppelklick (Scanner): {e}")
            traceback.print_exc()

    # --- KORREKTUR (V8): Doppelklick für Tab 4 (OMS) ---
    def _on_oms_item_double_click(self, event):
        item_id = self.oms_tree.identify_row(event.y)
        if not item_id: return
        
        try:
            # 'item_id' ist jetzt der DataFrame-Index (iid=index)
            row_index = int(item_id)
            selected_journey = self.oms_journeys_df.loc[row_index]
            
            iata_to_find = selected_journey['IATA']
            journey_id_to_find = selected_journey['JourneyID'] # Lese die JourneyID
            
            if (iata_to_find == 'N/A' or pd.isna(iata_to_find)):
                 messagebox.showinfo("Info", "Keine IATA für diesen Eintrag vorhanden.", parent=self)
                 return
            
            # Rufe die History-Funktion mit IATA und JourneyID auf
            self._show_oms_history_window(iata_to_find, journey_id_to_find)
            
        except Exception as e:
            print(f"Fehler bei Doppelklick (OMS): {e}")
            traceback.print_exc()

    def _on_plc_item_double_click(self, event):
        item_id = self.plc_journey_tree.identify_row(event.y)
        if not item_id: return
        
        try:
            row_index = int(item_id)
            selected_journey_summary = self.plc_journeys_df.loc[row_index]
            
            iata_to_find = selected_journey_summary.get('IATA')
            journey_id_to_find = selected_journey_summary.get('JourneyID')
            
            if iata_to_find == 'N/A' or pd.isna(iata_to_find):
                messagebox.showinfo("Info", "Keine IATA für diesen Einzeleintrag vorhanden.", parent=self)
                return
            
            history_df = self.plc_raw_df[
                (self.plc_raw_df['IATA'] == iata_to_find) &
                (self.plc_raw_df['JourneyID'] == journey_id_to_find)
            ].sort_values(by="Timestamp")
            
            if history_df.empty:
                 history_df = self.plc_raw_df[
                    (self.plc_raw_df['IATA'] == iata_to_find)
                 ].sort_values(by="Timestamp")

            self._show_plc_history_window(iata_to_find, history_df)
            
        except (ValueError, TypeError, IndexError, KeyError) as e:
            print(f"Fehler bei PLC-Doppelklick (IID: {item_id}): {e}")
            traceback.print_exc()
            messagebox.showerror("Fehler", f"Konnte Detailansicht nicht laden:\n{e}", parent=self)

    def _extract_routing_info(self, history_df):
        info = {'iata': 'N/A', 'machine_decision': 'N/A', 'operator_decision': 'N/A', 'final_command': 'N/A', 'device': 'N/A'}
        if history_df.empty: return info
        
        valid_iatas = history_df['IATA'][(history_df['IATA'] != 'N/A') & (pd.notna(history_df['IATA']))]
        if not valid_iatas.empty: info['iata'] = valid_iatas.iloc[0]
        
        valid_devices = history_df['Device'][(history_df['Device'] != 'N/A') & (pd.notna(history_df['Device']))].unique()
        if len(valid_devices) > 0: info['device'] = valid_devices[0]

        machine_dec_df = history_df[history_df['Klartext'].str.contains("Maschinelle Entscheidung", na=False)]
        if not machine_dec_df.empty:
            match = re.search(r"Maschinelle Entscheidung \((EDS|LTR)\): \*\*(ALARM|CLEAR)\*\*", machine_dec_df.iloc[-1]['Klartext'])
            if match:
                info['machine_decision'] = f"{match.group(2)} ({match.group(1)})" # z.B. "ALARM (EDS)"
            
        op_dec_df = history_df[history_df['Klartext'].str.contains("Operator-Entscheidung", na=False)]
        if not op_dec_df.empty:
            last_op_klartext = op_dec_df.iloc[-1]['Klartext']
            match_op = re.search(r"von '([a-zA-Z0-9_]+)'", last_op_klartext)
            match_disp = re.search(r":\s*(.+)", last_op_klartext)
            op = match_op.group(1) if match_op else 'N/A'
            disp = match_disp.group(1).replace("**", "") if match_disp else 'N/A'
            info['operator_decision'] = f"{disp} (von {op})"
        
        final_cmd_df = history_df[history_df['Klartext'].str.contains("Finaler Befehl an Förderanlage", na=False)]
        if not final_cmd_df.empty:
            match = re.search(r"gesendet: (.+)", final_cmd_df.iloc[-1]['Klartext'])
            if match: info['final_command'] = match.group(1).replace("**", "")
        # V15: Angepasste Fallback-Logik (muss die Logik aus data_processor widerspiegeln)
        elif info['operator_decision'] != 'N/A' and '(von N/A)' not in info['operator_decision']:
            op_name = re.search(r"\(von (operator\d)\)", info['operator_decision'])
            if op_name and op_name.group(1) in ['operator3', 'operator4']:
                info['final_command'] = info['operator_decision'].split(' (')[0]
        # (Wenn Op 1/2, bleibt Final N/A, es sei denn OMS hat es)

        return info

    def _show_bag_history_window(self, bag_id, iata):
        win = tk.Toplevel(self); win.title(f"Scanner-Detail: {bag_id} | IATA: {iata}"); win.geometry("1100x800")
        
        # KORREKTUR (V14): Filtert Rohdaten nach BagID UND IATA
        history_df = self.scanner_raw_df[
            (self.scanner_raw_df['BagID'] == bag_id) & 
            (self.scanner_raw_df['IATA'] == iata)
        ].sort_values(by="Timestamp")
        
        routing_info = self._extract_routing_info(history_df)
        
        summary_frame = ttk.LabelFrame(win, text="Analyse-Ergebnis (nur Scanner-Log)", padding=10); summary_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(summary_frame, text="IATA:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(summary_frame, text=iata).grid(row=0, column=1, sticky="w")
        ttk.Label(summary_frame, text="Gerät (CCT):", font=("Helvetica", 10, "bold")).grid(row=0, column=2, sticky="w", padx=(20, 5))
        ttk.Label(summary_frame, text=routing_info['device']).grid(row=0, column=3, sticky="w")
        ttk.Label(summary_frame, text="Maschinen-Entscheid:", font=("Helvetica", 10, "bold")).grid(row=1, column=0, sticky="w")
        ttk.Label(summary_frame, text=routing_info['machine_decision']).grid(row=1, column=1, sticky="w")
        ttk.Label(summary_frame, text="Operator-Entscheid:", font=("Helvetica", 10, "bold")).grid(row=2, column=0, sticky="w")
        ttk.Label(summary_frame, text=routing_info['operator_decision']).grid(row=2, column=1, sticky="w")
        ttk.Label(summary_frame, text="Finale Entscheidung:", font=("Helvetica", 10, "bold")).grid(row=3, column=0, sticky="w")
        ttk.Label(summary_frame, text=routing_info['final_command']).grid(row=3, column=1, sticky="w")
        
        
        notebook = ttk.Notebook(win); notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        tab1 = ttk.Frame(notebook); notebook.add(tab1, text="Klartext-Analyse (Scanner)"); text1 = tk.Text(tab1, wrap=tk.WORD, font=("Courier New", 10)); text1.pack(fill=tk.BOTH, expand=True)
        tab2 = ttk.Frame(notebook); notebook.add(tab2, text="Scanner-Log Rohdaten"); text2 = tk.Text(tab2, wrap=tk.WORD, font=("Courier New", 9)); text2.pack(fill=tk.BOTH, expand=True)
        
        export_content = self._build_export_content(history_df, bag_id, routing_info, "Scanner")
        
        if not history_df.empty:
            header = f"Chronologische Analyse für BagID: {bag_id} (Wanne: {iata}, Gerät: {routing_info['device']})\n"; text1.insert(tk.END, header + "=" * len(header) + "\n\n")
            
            local_tz = pytz.timezone('Europe/Berlin')
            for _, row in history_df.iterrows(): 
                ts_local = row['Timestamp'].astimezone(local_tz)
                ts_str = ts_local.strftime('%H:%M:%S.%f')[:-3]
                full_line = f"[{ts_str}] {row['Klartext']}\n"; text1.insert(tk.END, full_line.replace("**", ""))
            
            for _, row in history_df.iterrows(): text2.insert(tk.END, row['OriginalLog'] + "\n")
        else:
            msg = f"Keine Scanner-Detail-Einträge für BagID {bag_id} / IATA {iata} gefunden."
            text1.insert(tk.END, msg); text2.insert(tk.END, msg)
            
        text1.config(state=tk.DISABLED); text2.config(state=tk.DISABLED)
        ttk.Button(win, text="Analyse speichern...", command=lambda: self._save_analysis(bag_id, iata, export_content)).pack(pady=10)

    # --- KORREKTUR (V8): Akzeptiert JourneyID ---
    def _show_oms_history_window(self, iata, journey_id):
        win = tk.Toplevel(self); win.title(f"OMS-Detail-Analyse für IATA: {iata} (Vorgang: {journey_id})"); win.geometry("1100x700")
        
        # Filtert Rohdaten nach IATA UND JourneyID (behebt 5-Minuten-Regel-Fehler)
        history_df = self.oms_raw_df[
            (self.oms_raw_df['IATA'] == iata) &
            (self.oms_raw_df['JourneyID'] == journey_id)
        ].sort_values(by="Timestamp")
        
        routing_info = self._extract_routing_info(history_df)
        
        summary_frame = ttk.LabelFrame(win, text="Analyse-Ergebnis (nur OMS-Log)", padding=10); summary_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(summary_frame, text="IATA:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(summary_frame, text=iata).grid(row=0, column=1, sticky="w")
        ttk.Label(summary_frame, text="Maschinen-Entscheid (falls gesehen):", font=("Helvetica", 10, "bold")).grid(row=1, column=0, sticky="w")
        ttk.Label(summary_frame, text=routing_info['machine_decision']).grid(row=1, column=1, sticky="w")
        ttk.Label(summary_frame, text="Operator-Entscheid (falls gesehen):", font=("Helvetica", 10, "bold")).grid(row=2, column=0, sticky="w")
        ttk.Label(summary_frame, text=routing_info['operator_decision']).grid(row=2, column=1, sticky="w")
        ttk.Label(summary_frame, text="Finaler OMS-Befehl:", font=("Helvetica", 10, "bold")).grid(row=3, column=0, sticky="w")
        ttk.Label(summary_frame, text=routing_info['final_command']).grid(row=3, column=1, sticky="w")

        notebook = ttk.Notebook(win); notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        tab1 = ttk.Frame(notebook); notebook.add(tab1, text="Klartext-Analyse (OMS)"); text1 = tk.Text(tab1, wrap=tk.WORD, font=("Courier New", 10)); text1.pack(fill=tk.BOTH, expand=True)
        tab2 = ttk.Frame(notebook); notebook.add(tab2, text="OMS-Log Rohdaten"); text2 = tk.Text(tab2, wrap=tk.WORD, font=("Courier New", 9)); text2.pack(fill=tk.BOTH, expand=True)
        
        export_content = self._build_export_content(history_df, "N/A", routing_info, "OMS")

        if not history_df.empty:
            header = f"Chronologische OMS-Analyse für IATA: {iata} (Vorgang: {journey_id})\n"; text1.insert(tk.END, header + "=" * len(header) + "\n\n")
            
            local_tz = pytz.timezone('Europe/Berlin')
            for _, row in history_df.iterrows(): 
                ts_local = row['Timestamp'].astimezone(local_tz)
                ts_str = ts_local.strftime('%H:%M:%S.%f')[:-3]
                full_line = f"[{ts_str}] {row['Klartext']}\n"; text1.insert(tk.END, full_line.replace("**", ""))
            
            for _, row in history_df.iterrows(): 
                ts_local = row['Timestamp'].astimezone(local_tz)
                ts_str = ts_local.strftime('%H:%M:%S.%f')[:-3]
                text2.insert(tk.END, f"[{ts_str}] {row['OriginalLog']}\n")
        else:
            msg = f"Keine OMS-Detail-Einträge für IATA {iata} (Vorgang: {journey_id}) gefunden."
            text1.insert(tk.END, msg); text2.insert(tk.END, msg)
            
        text1.config(state=tk.DISABLED); text2.config(state=tk.DISABLED)
        ttk.Button(win, text="Analyse speichern...", command=lambda: self._save_analysis("OMS", iata, export_content)).pack(pady=10)


    def _show_plc_history_window(self, iata, history_df):
        win = tk.Toplevel(self); win.title(f"SPS-Detail-Analyse für IATA: {iata}"); win.geometry("1100x700")
        
        summary_frame = ttk.LabelFrame(win, text="SPS-Vorgang (nur PlcLog.csv)", padding=10); summary_frame.pack(fill=tk.X, padx=10, pady=10)
        
        final_decision = "N/A"
        final_dec_df = history_df[history_df['Klartext'].str.contains("Entscheidung vom Scanner empfangen", na=False)]
        if not final_dec_df.empty:
            match = re.search(r"Decision \d \((CLEAR|REJECT)\)", final_dec_df.iloc[-1]['Klartext'])
            if match: final_decision = match.group(1)
        elif not history_df[history_df['Klartext'].str.contains("FEHLER:", na=False)].empty:
            final_decision = "ERROR"

        ttk.Label(summary_frame, text="IATA:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(summary_frame, text=iata).grid(row=0, column=1, sticky="w")
        ttk.Label(summary_frame, text="Finale Entscheidung:", font=("Helvetica", 10, "bold")).grid(row=0, column=2, sticky="w", padx=(20, 5))
        ttk.Label(summary_frame, text=final_decision).grid(row=0, column=3, sticky="w")

        notebook = ttk.Notebook(win); notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        tab1 = ttk.Frame(notebook); notebook.add(tab1, text="Klartext-Analyse (IATA-bezogen)"); text1 = tk.Text(tab1, wrap=tk.WORD, font=("Courier New", 10)); text1.pack(fill=tk.BOTH, expand=True)
        tab2 = ttk.Frame(notebook); notebook.add(tab2, text="Original-Log Auszug (IATA-bezogen)"); text2 = tk.Text(tab2, wrap=tk.WORD, font=("Courier New", 9)); text2.pack(fill=tk.BOTH, expand=True)

        if not history_df.empty:
            header = f"Chronologische SPS-Analyse für IATA: {iata}\n"; text1.insert(tk.END, header + "=" * len(header) + "\n\n")
            for _, row in history_df.iterrows(): 
                ts_str = row['Timestamp'].strftime('%H:%M:%S') 
                full_line = f"[{ts_str}] {row['Klartext']}\n"; text1.insert(tk.END, full_line.replace("**", ""))
            
            for _, row in history_df.iterrows(): 
                text2.insert(tk.END, row['OriginalLog'] + "\n")
        else:
            msg = f"Keine Detail-Einträge für IATA {iata} gefunden."
            text1.insert(tk.END, msg)
            text2.insert(tk.END, msg)
            
        text1.config(state=tk.DISABLED); text2.config(state=tk.DISABLED)

    def _build_export_content(self, history_df, bag_id, routing_info, log_type="Scanner"):
        if history_df.empty: return f"Keine Detail-Einträge für {bag_id} gefunden."
        
        display_iata = routing_info['iata']
        
        content_parts = [
            f"ANALYSE-REPORT ({log_type.upper()}-LOG) FÜR BAGID {bag_id} (WANNE: {display_iata}, GERÄT: {routing_info['device']})", 
            f"Erstellt am: {datetime.now().strftime('%d.%m.%Y um %H:%M:%S Uhr')}", "="*60, 
            "\n--- ROUTING-ANALYSE ---", 
            f"IATA: {display_iata}", 
            f"Gerät: {routing_info['device']}",
            f"Maschinen-Entscheid: {routing_info['machine_decision']}", 
            f"Operator-Entscheid: {routing_info['operator_decision']}", 
            f"Finale Entscheidung: {routing_info['final_command']}\n", 
            f"--- KLARTEXT-ANALYSE ({log_type.upper()}-BEZOGEN) ---"
        ]
        
        history_df_no_duplicates = history_df.drop_duplicates(subset=['Klartext'])
        
        local_tz = pytz.timezone('Europe/Berlin')
        for _, row in history_df_no_duplicates.iterrows(): 
            ts_local = row['Timestamp'].astimezone(local_tz)
            ts_str = ts_local.strftime('%H:%M:%S.%f')[:-3]
            content_parts.append(f"[{ts_str}] {row['Klartext'].replace('**', '')}")
        
        content_parts.append(f"\n--- {log_type.upper()}-LOG AUSZUG ---")
        
        for _, row in history_df.iterrows(): 
            ts_local = row['Timestamp'].astimezone(local_tz)
            ts_str = ts_local.strftime('%H:%M:%S.%f')[:-3]
            content_parts.append(f"[{ts_str}] {row['OriginalLog']}")
        
        return "\n".join(content_parts)

    def _save_oms_report(self):
        if self.oms_raw_df.empty:
            messagebox.showerror("Fehler", "Keine OMS-Daten (roh) zum Analysieren vorhanden.", parent=self)
            return

        save_path = filedialog.asksaveasfilename(
            initialfile="iata_report_v13.txt",
            defaultextension=".txt",
            filetypes=[("Textdateien", "*.txt"), ("Alle Dateien", "*.*")]
        )
        if not save_path:
            return

        try:
            # Rufe die importierte Funktion auf
            success = generate_oms_report(self.oms_raw_df, save_path)
            if success:
                messagebox.showinfo("Erfolg", f"OMS-Report erfolgreich gespeichert unter:\n{save_path}", parent=self)
            else:
                messagebox.showerror("Fehler", "OMS-Report konnte nicht erstellt werden. Siehe Konsole für Details.", parent=self)
        except Exception as e:
            messagebox.showerror("Fehler", f"OMS-Report konnte nicht erstellt werden:\n{e}", parent=self)
            traceback.print_exc()

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

    def _show_iata_selection_window(self, matching_journeys):
         messagebox.showinfo("Info", "Mehrere Durchläufe für diese IATA gefunden. Zeige alle.", parent=self)
         self._update_treeview(matching_journeys)


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