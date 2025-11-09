# mv3d_app.py
# VERSION 2.6 - Finale Stabilitätsversion (GateView-Logik)
# - FIX: Ersetzt das fehlerhafte 'DateEntry'-Widget durch eine stabile 'Combobox'
#   (Logik kopiert von system_analyzer_app.py).
# - Dies behebt den "1 Eintrag" / "13 Einträge" Anzeigefehler endgültig.
# - (Behält alle vorherigen Fixes bei: Stabilitäts-Limit, Doppelklick, Einrückung)

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, font as tkfont
import pandas as pd
import threading
import os
import re
import sys
import traceback
import multiprocessing
from datetime import datetime, timedelta, date

# --- IMPORTE ---
try:
    # WIRD NICHT MEHR BENÖTIGT
    # from tkcalendar import DateEntry 
    pass
except ImportError:
    pass # Ignorieren, da wir es nicht mehr verwenden

try:
    from mv3d_casefile_window import MV3DCasefileWindow
except ImportError:
    print("WARNUNG: mv3d_casefile_window.py nicht gefunden. Detailansicht deaktiviert.")
    class MV3DCasefileWindow:
        def __init__(self, parent, selected_row, raw_df):
            messagebox.showerror("Fehler", "Detailfenster (mv3d_casefile_window.py) nicht geladen.", parent=parent)
            win = tk.Toplevel(parent); win.title("Fehler"); ttk.Label(win, text="Detailfenster nicht geladen.").pack(padx=20, pady=20)

try:
    import sv_ttk
    from base_app import BaseApp
    import config_manager as cfg
    from ftp_dialog_advanced import AdvancedFTPDialog
    from ftp_client import SFTPClient
    from sftp_log_window import SFTPLogWindow
    from ftp_file_selection_dialog import FTPFileSelectionDialog
    from help_texts import MV3D_HELP_TEXT
    from mv3d_log_parser import MV3DLogParser 
    from log_previewer import preview_log_directory
except ImportError as e:
    error_message = f"Ein kritischer Import-Fehler ist aufgetreten:\n\nDie Datei '{e.name}.py' oder die Bibliothek '{e.name}' konnte nicht gefunden werden.\n\n{traceback.format_exc()}"
    print(error_message) 
    with open("mv3d_crash_report.log", "w", encoding='utf-8') as f:
        f.write(error_message)
    root = tk.Tk()
    root.withdraw() 
    messagebox.showerror("Kritischer Fehler", f"Ein Modul konnte nicht geladen werden: {e.name}\n\nDas Programm wird beendet. Details in 'mv3d_crash_report.log'.")
    sys.exit(1)


class MV3DApp(BaseApp):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, app_name="MV3D Analyzer", version="2.6 (GateView-Logik)", *args, **kwargs)
        
        self.raw_df = pd.DataFrame()
        self.incidents_df = pd.DataFrame()
        self.filtered_incidents_df = pd.DataFrame() 
        self.loading_win = None
        self.source_dir = None
        
        self.parser = MV3DLogParser() 
        
        self.local_date_filter_mode = tk.StringVar(value="all")
        self.local_date_filter_days = tk.StringVar(value="2")
        
        self.selection_event = threading.Event()
        self.user_selection = None
        
        self.search_entry = None
        self.errorcode_entry = None
        self.source_filter_combo = None
        self.severity_filter_combo = None
        self.date_filter_combo = None
        self.tree = None
        
        self.estop_var = tk.BooleanVar(value=False)
        self.hvps_var = tk.BooleanVar(value=False)
        self.bagjam_var = tk.BooleanVar(value=False)
        self.license_var = tk.BooleanVar(value=False)
        
        self._setup_ui()
        self._check_config_for_last_dir()

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- OBERER LADE-BEREICH ---
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=5)
        ttk.Button(control_frame, text="1. Lokalen Ordner laden...", command=self._load_logs_from_dialog, style='Accent.TButton').pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(control_frame, text="Logs von FTP laden...", command=self._open_ftp_dialog_mv3d).pack(side=tk.LEFT, padx=5, pady=5)

        filter_frame = ttk.Frame(control_frame)
        filter_frame.pack(side=tk.LEFT, padx=15)
        ttk.Label(filter_frame, text="Filter für Lokale Suche:").pack(side=tk.LEFT, padx=(5, 10))
        rb_all = ttk.Radiobutton(filter_frame, text="Alle Logs im Ordner", variable=self.local_date_filter_mode, value="all")
        rb_all.pack(side=tk.LEFT)
        rb_days = ttk.Radiobutton(filter_frame, text="Nur die letzten", variable=self.local_date_filter_mode, value="days")
        rb_days.pack(side=tk.LEFT, padx=(10, 0))
        entry_days = ttk.Entry(filter_frame, textvariable=self.local_date_filter_days, width=3)
        entry_days.pack(side=tk.LEFT, padx=5)
        ttk.Label(filter_frame, text="Tage").pack(side=tk.LEFT)
        
        preview_frame = ttk.Frame(main_frame)
        preview_frame.pack(fill=tk.X, pady=(0, 10))
        self.preview_label = ttk.Label(preview_frame, text="Kein Ordner geladen.")
        self.preview_label.pack(side=tk.LEFT, padx=5)
        
        # --- FILTER-UI ---
        filter_frame1 = ttk.Frame(main_frame)
        filter_frame1.pack(fill=tk.X, pady=(5, 2), padx=5)
        ttk.Label(filter_frame1, text="Suchen (Log):").pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = ttk.Entry(filter_frame1, width=30); self.search_entry.pack(side=tk.LEFT, padx=5); self.search_entry.bind("<Return>", self._apply_filters)
        ttk.Label(filter_frame1, text="Fehlercode (Regex):").pack(side=tk.LEFT, padx=(10, 5))
        self.errorcode_entry = ttk.Entry(filter_frame1, width=20); self.errorcode_entry.pack(side=tk.LEFT, padx=5); self.errorcode_entry.bind("<Return>", self._apply_filters)
        ttk.Label(filter_frame1, text="Datei:").pack(side=tk.LEFT, padx=(10, 5))
        self.source_filter_combo = ttk.Combobox(filter_frame1, state="readonly", width=25)
        self.source_filter_combo.pack(side=tk.LEFT, padx=5); self.source_filter_combo.set('Alle'); self.source_filter_combo.bind("<<ComboboxSelected>>", self._apply_filters)
        
        filter_frame2 = ttk.Frame(main_frame)
        filter_frame2.pack(fill=tk.X, pady=(2, 5), padx=5)
        ttk.Label(filter_frame2, text="Fehler-Typen:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Checkbutton(filter_frame2, text="E-Stop", variable=self.estop_var, command=self._apply_filters).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(filter_frame2, text="HVPS", variable=self.hvps_var, command=self._apply_filters).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(filter_frame2, text="Bag Jam", variable=self.bagjam_var, command=self._apply_filters).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(filter_frame2, text="License", variable=self.license_var, command=self._apply_filters).pack(side=tk.LEFT, padx=2)
        ttk.Label(filter_frame2, text="Stufe:").pack(side=tk.LEFT, padx=(10, 5))
        self.severity_filter_combo = ttk.Combobox(filter_frame2, state="readonly", width=12, values=['Alle'])
        self.severity_filter_combo.pack(side=tk.LEFT, padx=5); self.severity_filter_combo.set('Alle'); self.severity_filter_combo.bind("<<ComboboxSelected>>", self._apply_filters)
        ttk.Label(filter_frame2, text="Datum:").pack(side=tk.LEFT, padx=(10, 5))
        
        # --- KORREKTUR: DateEntry ERSETZT durch Combobox ---
        self.date_filter_combo = ttk.Combobox(filter_frame2, state="readonly", width=15)
        self.date_filter_combo.pack(side=tk.LEFT, padx=5); self.date_filter_combo.set('Alle')
        self.date_filter_combo.bind("<<ComboboxSelected>>", self._apply_filters)
        # --- ENDE KORREKTUR ---
        
        ttk.Button(filter_frame2, text="Alle Filter zurücksetzen", command=self._reset_all_filters).pack(side=tk.LEFT, padx=15)

        # --- LOG-FRAME ---
        log_frame = ttk.LabelFrame(main_frame, text="Gefundene System-Ereignisse", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(5,0))
        self.tree = ttk.Treeview(log_frame, columns=("Timestamp", "Severity", "SourceFile", "Event"), show="headings")
        self.tree.heading("Timestamp", text="Zeitpunkt"); self.tree.column("Timestamp", width=150, anchor="w"); 
        self.tree.heading("Severity", text="Stufe"); self.tree.column("Severity", width=80, anchor="center"); 
        self.tree.heading("SourceFile", text="Quelldatei", anchor="w"); self.tree.column("SourceFile", width=200, anchor="w"); 
        self.tree.heading("Event", text="Ereignis"); self.tree.column("Event", width=650)
        self.tree.bind("<Double-1>", self._on_item_select) 
        
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        try: 
            default_font = tkfont.nametofont("TkDefaultFont"); self.bold_font = default_font.copy(); self.bold_font.configure(weight="bold")
        except tk.TclError: 
            self.bold_font = None 
            
        self.tree.tag_configure("E-STOP", foreground="#FF5252", font=self.bold_font)
        self.tree.tag_configure("FAULT", foreground="#FF5252", font=self.bold_font)
        self.tree.tag_configure("GENERIC", foreground="#FF8A80") 
        self.tree.tag_configure("HVPS", foreground="#FF8A80")
        self.tree.tag_configure("COMM", foreground="#FF8A80")
        self.tree.tag_configure("TIMEOUT", foreground="#FF8A80")
        self.tree.tag_configure("BAG-JAM", foreground="#FFD180") 
        self.tree.tag_configure("TEMP", foreground="#FFD180")
        self.tree.tag_configure("BNA", foreground="#FFD180")
        self.tree.tag_configure("WARNING", foreground="#FFD180")
        self.tree.tag_configure("AUTH", foreground="#80CBC4") 
        self.tree.tag_configure("PLC", foreground="#80CBC4")
        self.tree.tag_configure("DPP", foreground="#80CBC4")
        self.tree.tag_configure("IAC", foreground="#80CBC4")

        self.status_label = ttk.Label(self.status_bar, text="Bereit. Bitte Log-Ordner laden.")
        self.status_label.pack(side=tk.LEFT, padx=5)

    def _check_config_for_last_dir(self):
        config = cfg.load_config()
        last_dir = config.get("last_mv3d_dir")
        if last_dir and os.path.exists(last_dir):
            self.source_dir = last_dir
            self._update_preview_label()
            
    def _update_preview_label(self):
        if not self.source_dir or not os.path.exists(self.source_dir):
            self.preview_label.config(text="Kein gültiger Ordner geladen.")
            return
        self.preview_label.config(text=f"Prüfe Ordner: {os.path.basename(self.source_dir)}...")
        thread = threading.Thread(target=self._run_preview_thread, args=(self.source_dir,), daemon=True)
        thread.start()

    def _run_preview_thread(self, dir_path):
        try:
            min_date, max_date, count = preview_log_directory(dir_path, self.parser.PARSER_MAP)
            if min_date and max_date:
                date_str = f"Zeitraum: {min_date.strftime('%Y-%m-%d')} bis {max_date.strftime('%Y-%m-%d')}"
                count_str = f"{count:,} Einträge (geschätzt)"
                text = f"Ordner: {os.path.basename(dir_path)}  |  {date_str}  |  {count_str}"
            else:
                text = f"Ordner: {os.path.basename(dir_path)} (Keine relevanten Logs gefunden)"
            self.after(0, self.preview_label.config, {"text": text})
        except Exception as e:
            print(f"Fehler bei der Log-Vorschau: {e}")
            self.after(0, self.preview_label.config, {"text": "Fehler bei der Ordner-Vorschau."})

    # --- LOKALER LADEPROZESS (ANGEPASST FÜR RELATIVES DATUM) ---

    def _load_logs_from_dialog(self):
        config = cfg.load_config()
        last_dir = config.get("last_mv3d_dir", os.getcwd())
        dir_path = filedialog.askdirectory(title="Wählen Sie den MV3D-Log-Download-Ordner", initialdir=last_dir)
        if not dir_path:
            return
            
        self.source_dir = dir_path
        config["last_mv3d_dir"] = dir_path
        cfg.save_config(config)
        self._update_preview_label()
        
        file_date_cache = {} 
        
        self.status_label.config(text="Suche nach Log-Dateien (Schritt 1/2)...")
        _, max_date = self._collect_local_log_files(self.source_dir, None, file_date_cache) 
        
        if max_date:
            print(f"--- Letztes Datum im Ordner gefunden: {max_date.date()} ---")

        date_range = self._get_local_date_filter(max_date) 

        self.status_label.config(text="Suche nach Log-Dateien (Schritt 2/2)...")
        log_files, _ = self._collect_local_log_files(self.source_dir, date_range, file_date_cache)
        
        if not log_files:
            messagebox.showwarning("Keine Logs", "Keine Log-Dateien gefunden, die dem Filter entsprechen.", parent=self)
            self.status_label.config(text="Bereit.")
            return
            
        file_map = {'Lokale Dateien': log_files}
        dialog = FTPFileSelectionDialog(self, file_map)
        selected_map = dialog.show()
        
        if not selected_map:
            self.status_label.config(text="Analyse vom Benutzer abgebrochen.")
            return

        final_file_list = selected_map.get('Lokale Dateien', [])
        if not final_file_list:
            self.status_label.config(text="Keine Dateien zur Analyse ausgewählt.")
            return

        self.status_label.config(text=f"Analysiere {len(final_file_list)} ausgewählte Dateien...")
        self._start_loading_process(final_file_list, is_local=True)

    def _get_local_date_filter(self, max_log_date=None): 
        date_range = None
        try:
            mode = self.local_date_filter_mode.get()
            if mode == "days":
                if max_log_date:
                    end_date = max_log_date.replace(hour=23, minute=59, second=59)
                    print(f"--- Datumsfilter 'Tage' basiert auf Log-Maximum: {end_date.date()} ---")
                else:
                    end_date = datetime.now().replace(hour=23, minute=59, second=59)
                    print(f"--- WARNUNG: Datumsfilter 'Tage' basiert auf HEUTE (kein max. Log-Datum gefunden) ---")

                days = int(self.local_date_filter_days.get())
                if days <= 0: days = 1
                
                start_date = (end_date - timedelta(days=days-1)).replace(hour=0, minute=0, second=0)
                date_range = (start_date, end_date)
                self.status_label.config(text=f"Lokaler Filter: {start_date.date()} bis {end_date.date()}")
            else:
                self.status_label.config(text="Lokaler Filter: Alle Logs.")
        except Exception as e:
            print(f"Fehler bei lokaler Datumsberechnung: {e}")
            self.status_label.config(text="Fehler im Datumsfilter. Lade alle Logs.")
        return date_range

    def _get_file_date_from_path(self, file_path, cache):
        if file_path in cache:
            return cache[file_path]
        
        file_date = None
        match = re.search(r'-(\d{8})', os.path.basename(file_path))
        if match:
            try:
                file_date = datetime.strptime(match.group(1), '%Y%m%d')
            except ValueError:
                pass
        
        if file_date is None:
            try:
                mtime = os.path.getmtime(file_path)
                file_date = datetime.fromtimestamp(mtime)
            except OSError:
                cache[file_path] = None
                return None
        
        cache[file_path] = file_date
        return file_date

    def _check_file_daterange(self, file_path, date_range, file_date_cache):
        start_date, end_date = date_range
        end_date = end_date.replace(hour=23, minute=59, second=59)
        
        file_date = self._get_file_date_from_path(file_path, file_date_cache)
        
        if not file_date:
            return False 

        result = (start_date <= file_date <= end_date)
        match = re.search(r'-(\d{8})', os.path.basename(file_path))
        if not match: 
            if file_date >= start_date:
                result = True
            else:
                if file_date >= (start_date - timedelta(days=7)):
                     result = True
                else:
                     result = False
        return result

    def _collect_local_log_files(self, source_dir, date_range_filter, file_date_cache):
        matching_files = []
        max_date_found = None 

        for root, _, files in os.walk(source_dir, topdown=True):
            if any(d in root for d in ['/proc/', '/sys/', '/dev/']):
                continue
            if os.path.normpath(root).startswith(os.path.join(os.getcwd(), "Analyse")):
                continue
                
            for file in files:
                file_path = os.path.join(root, file)
                
                file_date = self._get_file_date_from_path(file_path, file_date_cache)
                if file_date:
                    if max_date_found is None or file_date > max_date_found:
                        max_date_found = file_date
                
                if date_range_filter:
                    if not self._check_file_daterange(file_path, date_range_filter, file_date_cache):
                        continue
                        
                for parser_name, info in self.parser.PARSER_MAP.items():
                    if re.match(info['file_pattern'], file):
                        matching_files.append(file_path)
                        break 
                        
        return matching_files, max_date_found 

    # --- ANALYSE-PROZESS ---
    def _start_loading_process(self, file_list_to_process, is_local=False):
        self._create_loading_window("Analysiere MV3D Logs...")
        self.raw_df = pd.DataFrame()
        self.incidents_df = pd.DataFrame()
        
        self._reset_all_filters() 
        self._update_treeview(pd.DataFrame())
        
        thread = threading.Thread(target=self._run_analysis_thread, args=(file_list_to_process, is_local), daemon=True)
        thread.start()
        self.after(100, self._check_thread, thread)

    def _run_analysis_thread(self, file_list, is_local):
        try:
            def progress_callback(progress, message):
                self.after(0, self._update_progress, progress, message)
            
            self.incidents_df, self.raw_df = self.parser.run_full_analysis(
                file_list, 
                progress_callback,
                is_local=is_local
            )
            self.thread_success = True 
        except Exception as e:
            self.thread_success = False
            error_message = f"Ein Fehler ist während der MV3D-Analyse aufgetreten:\n\n{traceback.format_exc()}"
            print(error_message)
            with open("mv3d_crash_report.log", "w", encoding='utf-8') as f:
                f.write(error_message)
            self.after(0, messagebox.showerror, "Analyse-Fehler", f"Ein schwerer Fehler ist aufgetreten:\n{e}\n\nDetails in 'mv3d_crash_report.log'.")

    def _check_thread(self, thread):
        if thread.is_alive():
            self.after(100, self._check_thread, thread)
        else:
            self.after(100, self._finalize_loading)

    # --- FINALIZE_LOADING (KORRIGIERT: Setzt alle Filter zurück) ---
    def _finalize_loading(self):
        if self.loading_win and self.loading_win.winfo_exists():
            self.loading_win.destroy()
            self.loading_win = None
            
        if not hasattr(self, 'thread_success') or not self.thread_success:
            self.status_label.config(text="Analyse fehlgeschlagen. Siehe 'mv3d_crash_report.log'.")
            return
            
        if not self.incidents_df.empty:
            try:
                self.incidents_df.rename(columns={'Category': 'Severity'}, inplace=True)
                print("--- Spalte 'Category' zu 'Severity' umbenannt für UI-Kompatibilität ---")
            except Exception as e:
                print(f"WARNUNG: Konnte Spalte nicht umbenennen: {e}")
        
        if self.incidents_df.empty and self.raw_df.empty:
            msg = "Analyse abgeschlossen. Keine lesbaren Log-Einträge in der Auswahl gefunden."
            self.status_label.config(text=msg)
            messagebox.showinfo("Analyse abgeschlossen", msg, parent=self)
        elif self.incidents_df.empty:
             msg = f"Analyse abgeschlossen. {len(self.raw_df)} Log-Einträge, aber 0 relevante System-Ereignisse gefunden."
             self.status_label.config(text=msg)
             messagebox.showinfo("Analyse abgeschlossen", msg, parent=self)
        else:
            msg = f"Analyse abgeschlossen. {len(self.incidents_df)} System-Ereignisse gefunden."
            self.status_label.config(text=msg)
            messagebox.showinfo("Analyse abgeschlossen", msg, parent=self)
        
        
        # --- JETZT DIE UI FÜLLEN (LOGIK v2.6) ---
        self.filtered_incidents_df = self.incidents_df.copy()
        
        # 1. Filter-Listen füllen (Dateinamen, Severities, Datumsbereich)
        self._populate_filters()
        
        # 2. Alle Filter zurücksetzen (setzt Datum auf "Alle") und Tabelle füllen.
        #    Dies ist jetzt STABIL, da wir eine Combobox statt DateEntry verwenden.
        self._reset_all_filters()
        
        print(f"--- UI aktualisiert. {len(self.incidents_df)} Einträge geladen. Anzeige wird durch _apply_filters() gesteuert. ---")
            
    # --- FTP-FUNKTIONEN ---
    def _open_ftp_dialog_mv3d(self):
        dialog = AdvancedFTPDialog(self, app_name="mv3d")
        ftp_details = dialog.show() 
        if ftp_details:
            log_win = SFTPLogWindow(self)
            thread = threading.Thread(target=self._run_sftp_download_mv3d, args=(ftp_details, log_win), daemon=True)
            thread.start()

    def _run_sftp_download_mv3d(self, profile, log_win):
        targets = profile.get("targets", {})
        date_filter = {
            "mode": profile.get("date_filter_mode", "all"),
            "days": profile.get("date_filter_days", 2)
        }
        
        def log_callback(message): 
            self.after(0, log_win.log, message)
        
        try:
            all_found_files_map = {} 
            
            for system_name, details in targets.items():
                host = details.get("host")
                if not host: 
                    continue
                
                log_callback(f"--- Verbinde mit {system_name} ({host}) für Dateiliste ---")
                self.after(0, self.set_connection_status, "connected")
                client = SFTPClient(host, details.get("user"), details.get("passwd"), details.get("port", "22"))
                message, success = client.connect(log_callback)
                
                if not success:
                    log_callback(f"FEHLER: Verbindung zu {system_name} fehlgeschlagen: {message}")
                    self.after(0, self.set_connection_status, "error")
                    client.disconnect()
                    continue

                log_callback("Suche nach Dateien auf dem Server...")
                remote_paths = details.get("paths", [])
                
                found_files = client.list_all_files_from_dir(remote_paths, log_callback, date_filter)
                
                if found_files:
                    all_found_files_map[system_name] = found_files
                
                log_callback(f"{len(found_files)} Dateien auf {system_name} gefunden.")
                client.disconnect()
                self.after(0, self.set_connection_status, "disconnected")
            
            if not all_found_files_map:
                log_callback("Keine Dateien auf keinem System gefunden, die dem Filter entsprechen.")
                self.after(3000, log_win.close_window)
                return

            self.selection_event.clear() 
            self.user_selection = None
            
            def open_dialog():
                dialog = FTPFileSelectionDialog(self, all_found_files_map)
                self.user_selection = dialog.show() 
                self.selection_event.set() 
                
            self.after(0, open_dialog)
            
            log_callback("Warte auf Benutzerauswahl im Dialog...")
            self.selection_event.wait() 
            
            selected_files_map = self.user_selection
            
            if not selected_files_map:
                log_callback("Benutzer hat Download abgebrochen.")
                self.after(3000, log_win.close_window)
                return
            
            log_callback(f"Auswahl getroffen. Starte Download für {len(selected_files_map)} System(e)...")

            final_downloaded_list = []
            has_errors = False
            
            local_download_dir = self.parser._prepare_analysis_dir()

            for system_name, files_to_get in selected_files_map.items():
                if not files_to_get:
                    continue
                
                details = targets[system_name] 
                
                log_callback(f"--- Verbinde erneut mit {system_name} für Download ---")
                self.after(0, self.set_connection_status, "connected")
                client = SFTPClient(details.get("host"), details.get("user"), details.get("passwd"), details.get("port", "22"))
                message, success = client.connect(log_callback)
                
                if not success:
                    log_callback(f"FEHLER: Verbindung zu {system_name} fehlgeschlagen.")
                    has_errors = True
                    self.after(0, self.set_connection_status, "error")
                    client.disconnect()
                    continue

                message, downloaded = client.download_selected_files(files_to_get, local_download_dir, log_callback)
                
                client.disconnect()
                self.after(0, self.set_connection_status, "disconnected")
                
                if not downloaded:
                    has_errors = True
                    log_callback(f"Fehler beim Download von {system_name}: {message}")
                else:
                    final_downloaded_list.extend(downloaded)

            if not final_downloaded_list and has_errors:
                log_callback("Download-Prozess mit Fehlern abgeschlossen.")
            elif final_downloaded_list:
                log_callback(f"Download abgeschlossen. Starte Analyse...")
                self.after(0, self.on_ftp_download_complete, final_downloaded_list)
            else:
                log_callback("Keine Dateien konnten heruntergeladen werden.")
                
        except Exception as e:
            log_callback(f"Ein schwerer Fehler im Download-Prozess ist aufgetreten: {e}")
            traceback.print_exc()
        
        self.after(3000, log_win.close_window)

    def on_ftp_download_complete(self, downloaded_files):
        if not downloaded_files:
            messagebox.showinfo("Download", "Keine Dateien heruntergeladen.", parent=self)
            return
        
        messagebox.showinfo("Download Abgeschlossen", f"{len(downloaded_files)} Datei(en) heruntergeladen.\nAnalyse wird gestartet.", parent=self)
        self._start_loading_process(downloaded_files, is_local=False)

    # --- Hilfsfunktionen (Loading Window, Help) ---
    def _create_loading_window(self, title="Ladevorgang"):
        self.loading_win = tk.Toplevel(self.parent)
        self.loading_win.title(title)
        self.loading_win.geometry("450x130")
        self.loading_win.resizable(False, False)
        self.parent.update_idletasks()
        x = self.parent.winfo_screenwidth() // 2 - self.loading_win.winfo_width() // 2
        y = self.parent.winfo_screenheight() // 2 - self.loading_win.winfo_height() // 2
        self.loading_win.geometry(f"+{x}+{y}")
        self.loading_win.transient(self.parent); self.loading_win.grab_set()
        self.loading_label = ttk.Label(self.loading_win, text="Initialisiere...", font=("Helvetica", 10))
        self.loading_label.pack(pady=(15, 5), padx=10, anchor="w")
        self.loading_progress_bar = ttk.Progressbar(self.loading_win, orient="horizontal", mode="determinate")
        self.loading_progress_bar.pack(fill=tk.X, expand=True, padx=10)
        self.percent_label = ttk.Label(self.loading_win, text="0%", font=("Helvetica", 10))
        self.percent_label.pack(pady=5)

    def _update_progress(self, progress, message):
        if self.loading_win and self.loading_win.winfo_exists():
            try:
                self.loading_win.lift()
                self.loading_label.config(text=f"{message}")
                self.loading_progress_bar['value'] = progress
                self.percent_label.config(text=f"{progress}%")
                self.loading_win.update_idletasks()
            except tk.TclError:
                pass 

    def _show_help_window(self):
        help_win = tk.Toplevel(self)
        help_win.title("Anleitung - MV3D Analyzer")
        help_win.geometry("800x600")
        help_win.transient(self); help_win.grab_set()
        text_area = scrolledtext.ScrolledText(help_win, wrap=tk.WORD, font=("Helvetica", 10), padx=10, pady=10)
        text_area.pack(expand=True, fill=tk.BOTH)
        text_area.insert(tk.INSERT, MV3D_HELP_TEXT) 
        text_area.config(state="disabled")

    # --- FILTER/UI FUNKTIONEN (ANGEPASST an Combobox) ---
    
    def _populate_filters(self):
        """Füllt die Filter-Comboboxen basierend auf den geladenen Daten."""
        self.severity_filter_combo.set('Alle')
        self.date_filter_combo.set('Alle')
        self.source_filter_combo.set('Alle')
        self.source_filter_combo['values'] = ['Alle']
        self.date_filter_combo['values'] = ['Alle'] # Beginnt mit 'Alle'
        self.date_filter_combo.config(state='disabled') # Deaktiviert bis Daten geladen sind

        base_df = self.incidents_df
        if base_df.empty: 
            return

        if 'SourceFile' in base_df.columns:
            unique_sources = sorted(base_df['SourceFile'].unique())
            if unique_sources: 
                self.source_filter_combo['values'] = ['Alle'] + unique_sources

        if 'Severity' in base_df.columns:
             unique_severities = sorted(base_df['Severity'].unique())
             if unique_severities:
                self.severity_filter_combo['values'] = ['Alle'] + unique_severities

        if 'Timestamp' in base_df.columns:
            valid_dates = base_df['Timestamp'].dropna()
            if not valid_dates.empty:
                # Logik von system_analyzer_app.py übernommen
                unique_dates = sorted(valid_dates.dt.date.unique(), reverse=True)
                self.date_filter_combo['values'] = ['Alle'] + [d.strftime('%Y-%m-%d') for d in unique_dates]
                self.date_filter_combo.config(state='readonly')

    def _apply_filters(self, event=None):
        """Wendet alle aktiven Filter auf die Treeview an."""
        if self.incidents_df.empty: 
            self._update_treeview(pd.DataFrame())
            self.status_label.config(text="Keine Daten zum Filtern.")
            return
            
        df_to_filter = self.incidents_df.copy()
        
        selected_severity = self.severity_filter_combo.get()
        selected_source = self.source_filter_combo.get()
        
        # --- KORRIGIERTE DATUMS-FILTERLOGIK (von system_analyzer_app.py) ---
        selected_date_str = self.date_filter_combo.get()
            
        if selected_severity and selected_severity != 'Alle': 
            df_to_filter = df_to_filter[df_to_filter['Severity'] == selected_severity]
        if selected_source and selected_source != 'Alle': 
            df_to_filter = df_to_filter[df_to_filter['SourceFile'] == selected_source]
            
        if selected_date_str and selected_date_str != 'Alle':
            try: 
                selected_date = pd.to_datetime(selected_date_str).date()
                df_to_filter = df_to_filter[df_to_filter['Timestamp'].dt.date == selected_date]
            except (ValueError, AttributeError):
                print(f"Ungültiger Datumswert: {selected_date_str}")
                pass # Ignoriere ungültiges Datum
        # --- ENDE KORREKTUR ---
            
        search_term = self.search_entry.get()
        if search_term:
            try: 
                df_to_filter = df_to_filter[df_to_filter['OriginalLog'].str.contains(search_term, case=False, regex=True, na=False)]
            except re.error: 
                messagebox.showwarning("Ungültige Suche", "Ungültige Regex.", parent=self.parent)
                
        errorcode_term = self.errorcode_entry.get()
        if errorcode_term:
            try: 
                df_to_filter = df_to_filter[df_to_filter['OriginalLog'].str.contains(errorcode_term, case=False, regex=True, na=False)]
            except re.error: 
                messagebox.showwarning("Ungültiger Fehlercode", "Ungültige Regex.", parent=self.parent)
                
        active_cb_filters = []
        if self.estop_var.get(): active_cb_filters.append('E-STOP')
        if self.hvps_var.get(): active_cb_filters.append('HVPS')
        if self.bagjam_var.get(): active_cb_filters.append('BAG-JAM')
        
        if active_cb_filters:
             df_to_filter = df_to_filter[df_to_filter['Severity'].isin(active_cb_filters)]

        self.filtered_incidents_df = df_to_filter
        self._update_treeview(self.filtered_incidents_df)

    def _reset_all_filters(self, event=None): 
        """Setzt alle Filter-UI-Elemente auf ihren Standard zurück."""
        self.severity_filter_combo.set('Alle')
        self.source_filter_combo.set('Alle')
        self.date_filter_combo.set('Alle') # KORRIGIERT (von '' auf 'Alle')
        if self.search_entry: self.search_entry.delete(0, tk.END)
        if self.errorcode_entry: self.errorcode_entry.delete(0, tk.END)
        self.estop_var.set(False)
        self.hvps_var.set(False)
        self.bagjam_var.set(False)
        self.license_var.set(False)
        self._apply_filters()

    def _update_treeview(self, df_to_show):
        """Aktualisiert die Baumansicht mit den Daten aus dem DataFrame."""
        if not self.tree: return 
        for i in self.tree.get_children(): self.tree.delete(i)
            
        if df_to_show is None or df_to_show.empty: 
            self.status_label.config(text="Keine Einträge für diese Filterauswahl gefunden.")
            return
        
        # --- STABILITÄTS-BEGRENZUNG (FIX für "nur 13 angezeigt") ---
        MAX_ROWS_TO_DISPLAY = 5000 
        
        if len(df_to_show) > MAX_ROWS_TO_DISPLAY:
            df_to_display_final = df_to_show.tail(MAX_ROWS_TO_DISPLAY)
            status_msg = f"Zeige die letzten {MAX_ROWS_TO_DISPLAY} von {len(df_to_show)} Einträgen."
            self.status_label.config(text=status_msg)
            messagebox.showwarning("Zu viele Daten", 
                                   f"Es wurden {len(df_to_show)} Einträge gefunden.\n\n"
                                   f"Um die Anwendung stabil zu halten, werden nur die letzten {MAX_ROWS_TO_DISPLAY} (neuesten) angezeigt.\n\n"
                                   "Bitte verwenden Sie die Filter (Datum, Stufe, Suche), um die Ergebnisse weiter einzuschränken.",
                                   parent=self)
        else:
            df_to_display_final = df_to_show
            self.status_label.config(text=f"{len(df_to_display_final)} Einträge nach Filterung.")
        # --- ENDE BEGRENZUNG ---

        for index, row in df_to_display_final.iterrows():
            tag = row['Severity'] if pd.notna(row['Severity']) else ''
            
            try:
                ts_str = row['Timestamp'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['Timestamp']) else 'N/A'
                
                self.tree.insert("", "end", iid=index, tags=(tag,), values=(
                    ts_str, 
                    row['Severity'], 
                    row['SourceFile'], 
                    row['OriginalLog']
                ))
            except Exception as e:
                print(f"Fehler beim Einfügen der Zeile {index} in Treeview: {e}")
                try:
                    self.tree.insert("", "end", iid=index, tags=("GENERIC",), values=(
                        "FEHLER", 
                        "DATEN", 
                        "KORRUPT", 
                        f"Index {index}: {e}"
                    ))
                except:
                    pass 

    def _on_item_select(self, event):
        """Öffnet das Detailfenster bei Doppelklick. (KORRIGIERTE LOGIK)"""
        selected_item_iid = self.tree.focus()
        if not selected_item_iid: return
            
        try:
            iid_int = int(selected_item_iid)
            
            if iid_int in self.filtered_incidents_df.index:
                
                selected_display_row = self.filtered_incidents_df.loc[iid_int]
                timestamp_match = selected_display_row['Timestamp']
                original_log_match = selected_display_row['OriginalLog']
                source_file_match = selected_display_row['SourceFile']

                potential_matches = self.raw_df[
                    (self.raw_df['Timestamp'] == timestamp_match) &
                    (self.raw_df['OriginalLog'] == original_log_match) &
                    (self.raw_df['SourceFile'] == source_file_match)
                ]
                
                if not potential_matches.empty:
                    selected_raw_row = self.raw_df.loc[potential_matches.index[0]]
                    MV3DCasefileWindow(self.parent, selected_raw_row, self.raw_df)
                else:
                    messagebox.showwarning("Fehler", "Zugehöriger Rohdaten-Eintrag nicht gefunden.", parent=self.parent)
            else:
                print(f"WARNUNG: Index {iid_int} nicht in filtered_incidents_df gefunden.")
                messagebox.showwarning("Fehler", "Ausgewählter Eintrag nicht gefunden (Indexproblem).", parent=self.parent)
        
        except (ValueError, KeyError, AttributeError, IndexError) as e:
            print(f"Fehler Öffnen Detailfenster (IID: {selected_item_iid}): {e}\n{traceback.format_exc()}")
            messagebox.showwarning("Fehler", "Detailansicht nicht möglich.", parent=self.parent)


# --- Zum Testen der App ---
if __name__ == "__main__":
    multiprocessing.freeze_support() 
    try:
        root = tk.Tk()
        sv_ttk.set_theme("dark") 
        app = MV3DApp(root)
        app.pack(fill="both", expand=True)
        root.mainloop()
    except Exception as e:
        error_message = f"Ein kritischer Fehler ist beim Start der MV3DApp aufgetreten:\n\n{traceback.format_exc()}"
        print(error_message)
        with open("mv3d_crash_report.log", "w", encoding='utf-8') as f:
            f.write(error_message)
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Kritischer Startfehler", f"Ein Fehler hat den Start verhindert: {e}\n\nDetails in 'mv3d_crash_report.log'.")
        except:
            pass