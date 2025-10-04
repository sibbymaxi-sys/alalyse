# mv3d_app.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import os
import threading
import re
import sys
import traceback
from datetime import timedelta
import multiprocessing

try:
    from base_app import BaseApp
    from error_manager import get_error_details
    from mv3d_definitions import SCS_OPERATING_STATES, TD_CODES, SD_CODES, SCS_FAULT_CODES
    import config_manager as cfg
    from timespan_dialog import TimespanDialog
    from log_previewer import preview_log_directory
    from ftp_dialog_advanced import AdvancedFTPDialog
    from ftp_client import SFTPClient
    from sftp_log_window import SFTPLogWindow
    from help_texts import MV3D_HELP_TEXT
    from concurrent.futures import ProcessPoolExecutor, as_completed
    from bhs_log_parser import parse_log as parse_bhs
    from bms_log_parser import parse_log as parse_bms
    from dpp_log_parser import parse_log as parse_dpp
    from plc_log_parser import parse_log as parse_plc
    from scs_log_parser import parse_log as parse_scs
    from iqtk_log_parser import parse_log as parse_iqtk
    from fsm_log_parser import parse_log as parse_fsm
except ImportError as e:
    with open("mv3d_crash_report.log", "w", encoding='utf-8') as f:
        f.write(f"Ein kritischer Import-Fehler ist aufgetreten:\n\nDie Datei '{e.name}.py' konnte nicht gefunden werden.\n\n")
        f.write(traceback.format_exc())
    sys.exit(1)

def parse_file_wrapper(path_and_parser):
    path, parser_func = path_and_parser
    return parser_func(path)

class MV3DApp(BaseApp):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, app_name="MV3D System Analyzer", version="1.0 Public", *args, **kwargs)
        self.combined_df = pd.DataFrame() 
        self.incidents_df = pd.DataFrame()
        self.loading_win = None
        self.parser_map = {
            "bhs.log": parse_bhs, "bms.log": parse_bms, "dpp.log": parse_dpp,
            "plc.log": parse_plc, "scs.log": parse_scs, "iqtk.log": parse_iqtk, "fsm.log": parse_fsm
        }
        self._setup_ui()

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding="10"); main_frame.pack(fill=tk.BOTH, expand=True)
        control_frame = ttk.Frame(main_frame); control_frame.pack(fill=tk.X, pady=5)
        ttk.Button(control_frame, text="Logs laden & Fall-Akten erstellen", command=self._load_from_dialog).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Label(control_frame, text="Nach Datum filtern:").pack(side=tk.LEFT, padx=(20, 5))
        self.date_filter_combo = ttk.Combobox(control_frame, state="readonly", width=15)
        self.date_filter_combo.pack(side=tk.LEFT, padx=5)
        self.date_filter_combo.bind("<<ComboboxSelected>>", self._on_date_filter_select)
        ttk.Button(control_frame, text="Filter zurücksetzen", command=self._reset_date_filter).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Zeige Rohdaten (Debug)", command=self._show_raw_data_debug).pack(side=tk.RIGHT, padx=5)
        incident_frame = ttk.LabelFrame(main_frame, text="Fall-Akten (kritische Ereignisse)", padding=10)
        incident_frame.pack(fill=tk.BOTH, expand=True, pady=(10,0))
        self.tree = ttk.Treeview(incident_frame, columns=("Timestamp", "Type", "RootCause"), show="headings")
        self.tree.heading("Timestamp", text="Zeitpunkt"); self.tree.column("Timestamp", width=150)
        self.tree.heading("Type", text="Fehler-Code", anchor="center"); self.tree.column("Type", width=120, anchor="center")
        self.tree.heading("RootCause", text="Beschreibung / Ursache"); self.tree.column("RootCause", width=600)
        self.tree.bind("<Double-1>", self._on_incident_select)
        scrollbar = ttk.Scrollbar(incident_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set); scrollbar.pack(side=tk.RIGHT, fill=tk.Y); self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.status_label = ttk.Label(self.status_bar, text="Bereit."); self.status_label.pack(side=tk.LEFT, padx=5)

    def _show_raw_data_debug(self):
        if self.combined_df.empty:
            messagebox.showinfo("Info", "Es wurden noch keine Log-Daten geladen.", parent=self)
            return
        win = tk.Toplevel(self)
        win.title("Rohdaten-Vorschau (erste 100 Zeilen)")
        win.geometry("900x600")
        text_area = scrolledtext.ScrolledText(win, wrap=tk.NONE, font=("Courier New", 9))
        text_area.pack(expand=True, fill=tk.BOTH)
        text_area.insert(tk.INSERT, self.combined_df[['Timestamp', 'Quelle', 'Ereignis', 'OriginalLog']].head(100).to_string())
        text_area.config(state="disabled")
        
    def _show_help_window(self):
        help_win = tk.Toplevel(self); help_win.title("Anleitung - MV3D Analyzer"); help_win.geometry("800x600"); help_win.transient(self); help_win.grab_set()
        text_area = scrolledtext.ScrolledText(help_win, wrap=tk.WORD, font=("Helvetica", 10), padx=10, pady=10); text_area.pack(expand=True, fill=tk.BOTH)
        text_area.insert(tk.INSERT, MV3D_HELP_TEXT); text_area.config(state="disabled")

    def _open_ftp_dialog(self):
        dialog = AdvancedFTPDialog(self, app_name="mv3d")
        sftp_details = dialog.show()
        if sftp_details:
            log_win = SFTPLogWindow(self)
            thread = threading.Thread(target=self._run_sequential_sftp_download, args=(sftp_details, log_win), daemon=True)
            thread.start()
            
    def _run_sequential_sftp_download(self, profile, log_win):
        local_dir = os.path.join(os.getcwd(), "logs", "mv3d_download")
        os.makedirs(local_dir, exist_ok=True)
        targets = profile.get("targets", {})
        all_downloaded_files = []; has_errors = False
        def log_callback(message): self.after(0, log_win.log, message)
        for system_name, details in targets.items():
            host = details.get("host")
            if not host: continue
            log_callback(f"--- Starte Verbindung zu {system_name} ({host}) ---")
            self.after(0, self.set_connection_status, "connected")
            client = SFTPClient(host, details.get("user"), details.get("passwd"), details.get("port", "22"))
            message, success = client.connect(log_callback)
            if success:
                log_callback(f"Erfolgreich mit {system_name} verbunden.")
                remote_paths = details.get("paths", [])
                message, downloaded = client.download_files(remote_paths, local_dir, log_callback)
                if not downloaded:
                    has_errors = True; log_callback(f"FEHLER beim Download von {system_name}: {message}"); self.after(0, self.set_connection_status, "error")
                else:
                    all_downloaded_files.extend(downloaded); log_callback(f"Erfolgreich {len(downloaded)} Datei(en) von {system_name} heruntergeladen.")
            else:
                has_errors = True; log_callback(f"FEHLER bei der Verbindung zu {system_name}: {message}"); self.after(0, self.set_connection_status, "error")
            log_callback(f"--- Trenne Verbindung zu {system_name} ---"); client.disconnect(); self.after(0, self.set_connection_status, "disconnected")
        if not all_downloaded_files and has_errors: log_callback("Download-Prozess mit Fehlern abgeschlossen.")
        elif all_downloaded_files: log_callback(f"Download abgeschlossen. Starte Analyse..."); self.after(0, self.on_ftp_download_complete, local_dir)
        else: log_callback("Keine Dateien zum Herunterladen gefunden.")
        self.after(3000, log_win.close_window)
        
    def on_ftp_download_complete(self, directory):
        self._process_directory(directory)

    def _load_from_dialog(self):
        config = cfg.load_config(); last_dir = config.get("last_mv3d_dir", os.getcwd())
        dir_path = filedialog.askdirectory(title="Wählen Sie das Haupt-Log-Verzeichnis", initialdir=last_dir)
        if not dir_path: return
        config["last_mv3d_dir"] = dir_path; cfg.save_config(config)
        self._process_directory(dir_path)

    def _process_directory(self, dir_path):
        self.status_label.config(text="Scanne Verzeichnis..."); self.update_idletasks()
        start_date, end_date, total_entries = preview_log_directory(dir_path, self.parser_map)
        self.status_label.config(text="Bereit.")
        if not start_date and not end_date:
            messagebox.showwarning("Keine Daten", f"Im Verzeichnis '{dir_path}' konnten keine Log-Dateien gefunden werden.", parent=self); return
        timespan_dialog = TimespanDialog(self, available_start=start_date, available_end=end_date, total_entries=total_entries)
        time_filter = timespan_dialog.show()
        if not time_filter: return
        self._start_loading_process(dir_path, time_filter)

    def _start_loading_process(self, dir_path, time_filter):
        self._create_loading_window()
        thread = threading.Thread(target=self._load_and_process_files, args=(dir_path, time_filter), daemon=True); thread.start()

    def _load_and_process_files(self, dir_path, time_filter):
        files_to_process = []
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file in self.parser_map: files_to_process.append((os.path.join(root, file), self.parser_map[file]))
        if not files_to_process:
            self.after(0, self._finalize_loading, False, f"Im Ordner '{dir_path}' wurden keine bekannten Log-Dateien gefunden.")
            return

        all_dfs = []
        processed_count = 0
        try:
            with ProcessPoolExecutor() as executor:
                future_to_filepath = {executor.submit(parse_file_wrapper, item): item[0] for item in files_to_process}
                for future in as_completed(future_to_filepath):
                    filepath = future_to_filepath[future]
                    filename = os.path.basename(filepath)
                    processed_count += 1
                    self.after(0, self._update_progress, processed_count, len(files_to_process) + 1, f"Verarbeite: {filename}")
                    df = future.result()
                    if not df.empty: all_dfs.append(df)
            
            if not all_dfs:
                self.after(0, self._finalize_loading, False, "Keine Log-Einträge in den Dateien gefunden.")
                return
            
            temp_df = pd.concat(all_dfs).sort_values(by="Timestamp").reset_index(drop=True)
            temp_df['Timestamp'] = pd.to_datetime(temp_df['Timestamp'])

            if not time_filter["load_all"]:
                self.combined_df = temp_df[(temp_df['Timestamp'] >= time_filter['start']) & (temp_df['Timestamp'] <= time_filter['end'])]
            else:
                self.combined_df = temp_df
            
            if self.combined_df.empty:
                self.after(0, self._finalize_loading, False, "Keine Log-Einträge im gewählten Zeitraum gefunden.")
                return
            
            self.after(0, self._update_progress, len(files_to_process) + 1, len(files_to_process) + 1, "Erstelle Fall-Akten...")
            self._identify_incidents_efficiently()
            
            message = f"{len(self.incidents_df)} kritische Ereignisse (Fall-Akten) wurden identifiziert."
            self.after(0, self._finalize_loading, True, message)

        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Fehler", f"Ein Fehler ist beim Verarbeiten aufgetreten:\n{e}", parent=self))
            self.after(0, self._finalize_loading, False, "Verarbeitung fehlgeschlagen.")

    def _finalize_loading(self, success, message):
        if self.loading_win: self.loading_win.destroy(); self.loading_win = None
        if success:
            self._update_incident_treeview()
            self._populate_date_filter()
            messagebox.showinfo("Analyse abgeschlossen", message, parent=self)
        else:
            messagebox.showwarning("Fehler", message, parent=self)

    def _identify_incidents_efficiently(self):
        incidents = []
        processed_indices = set()

        # Stufe 1: Spezifische Suche nach mfc= oder fault_cause=
        error_pattern_specific = r"(mfc=|fault_cause=)(\d+)"
        error_rows = self.combined_df[self.combined_df['OriginalLog'].str.contains(error_pattern_specific, na=False)]

        # Stufe 2: Fallback zur allgemeinen Suche nach ERROR/FAIL/FAULT
        if error_rows.empty:
            self.status_label.config(text="Keine spezifischen Fehlercodes gefunden. Starte allgemeine Fehlersuche...")
            self.update_idletasks()
            error_pattern_generic = r"(ERROR|FAIL|FAULT)"
            error_rows = self.combined_df[self.combined_df['OriginalLog'].str.contains(error_pattern_generic, case=False, na=False)]

        # Stufe 3: Fallback zur Suche nach Instabilitäts-Mustern
        if error_rows.empty:
            self.status_label.config(text="Keine allgemeinen Fehler gefunden. Suche nach Instabilitäts-Mustern...")
            self.update_idletasks()
            flapping_pattern = r"Ready To Receive Bit To BHS Low"
            error_rows = self.combined_df[self.combined_df['OriginalLog'].str.contains(flapping_pattern, na=False)]
        
        if error_rows.empty:
            self.incidents_df = pd.DataFrame(incidents)
            return

        # Verarbeitung der gefundenen Ereignisse
        for index, row in error_rows.iterrows():
            if index in processed_indices: continue

            error_timestamp = row['Timestamp']
            start_time = error_timestamp - timedelta(seconds=10)
            end_time = error_timestamp + timedelta(seconds=5)
            incident_df = self.combined_df[(self.combined_df['Timestamp'] >= start_time) & (self.combined_df['Timestamp'] <= end_time)]
            if incident_df.empty: continue

            error_code = "N/A"
            root_cause_text = "Allgemeiner Fehler"
            
            specific_match = re.search(error_pattern_specific, row['OriginalLog'])
            if specific_match:
                error_code = int(specific_match.group(2))
                root_cause_text, _, _ = get_error_details(error_code, row['OriginalLog'])
            elif 'Ready To Receive Bit To BHS Low' in row['OriginalLog']:
                error_code = "PLC-01"
                root_cause_text = "System-Instabilität (ReadyToReceive Flapping)"
            else:
                root_cause_text = row['Ereignis']

            incidents.append({
                'Timestamp': error_timestamp,
                'ErrorCode': error_code,
                'RootCause': root_cause_text,
                'data': incident_df
            })
            processed_indices.update(incident_df.index)
            
        self.incidents_df = pd.DataFrame(incidents)

    def _populate_date_filter(self):
        self.date_filter_combo.set('');
        if self.incidents_df.empty: self.date_filter_combo['values'] = []; return
        unique_dates = sorted(self.incidents_df['Timestamp'].dt.date.unique())
        self.date_filter_combo['values'] = [d.strftime('%Y-%m-%d') for d in unique_dates]

    def _on_date_filter_select(self, event=None):
        selected_date_str = self.date_filter_combo.get()
        if not selected_date_str: return
        selected_date = pd.to_datetime(selected_date_str).date()
        filtered_incidents = self.incidents_df[self.incidents_df['Timestamp'].dt.date == selected_date]
        self._update_incident_treeview(filtered_incidents)

    def _reset_date_filter(self):
        self.date_filter_combo.set(''); self._update_incident_treeview()

    def _update_incident_treeview(self, df=None):
        df_to_show = self.incidents_df if df is None else df
        for i in self.tree.get_children(): self.tree.delete(i)
        for index, row in df_to_show.iterrows():
            self.tree.insert("", "end", iid=index, values=(row['Timestamp'].strftime('%Y-%m-%d %H:%M:%S'), row['ErrorCode'], row['RootCause']))

    def _on_incident_select(self, event):
        selected_item = self.tree.focus()
        if not selected_item: return
        incident_index = int(selected_item); incident = self.incidents_df.loc[incident_index]
        self._show_case_file_window(incident)
        
    def _show_case_file_window(self, incident):
        error_code = incident['ErrorCode']
        error_name, error_description, recommended_action = get_error_details(error_code, incident['RootCause'])
        context_df = incident['data'][incident['data']['Timestamp'] < incident['Timestamp']]
        state_pattern = r"scs_machine=(\d+)"
        state_matches = context_df['OriginalLog'].str.extractall(state_pattern)
        last_state_text = "Unbekannt"
        if not state_matches.empty:
            last_state_code = int(state_matches.iloc[-1][0])
            last_state_text = f"{last_state_code} - {SCS_OPERATING_STATES.get(last_state_code, 'Unbekannt')}"
        win = tk.Toplevel(self); win.title(f"Fall-Akte: Fehler {error_code} um {incident['Timestamp'].strftime('%H:%M:%S')}")
        win.geometry("1000x800"); win.transient(self); win.grab_set()
        main_frame = ttk.Frame(win, padding=15); main_frame.pack(fill="both", expand=True)
        header_frame = ttk.LabelFrame(main_frame, text="Vorfalls-Analyse", padding=10); header_frame.pack(fill="x", pady=5)
        ttk.Label(header_frame, text="Fehler:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Label(header_frame, text=f"Code {error_code} - {error_name}", foreground="red", wraplength=800).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(header_frame, text="Beschreibung:", font=("Helvetica", 10, "bold")).grid(row=1, column=0, sticky="w", pady=2)
        ttk.Label(header_frame, text=error_description, wraplength=800).grid(row=1, column=1, sticky="w", padx=5)
        ttk.Label(header_frame, text="Empfehlung:", font=("Helvetica", 10, "bold")).grid(row=2, column=0, sticky="w", pady=2)
        ttk.Label(header_frame, text=recommended_action, wraplength=800).grid(row=2, column=1, sticky="w", padx=5)
        ttk.Label(header_frame, text="Letzter Zustand:", font=("Helvetica", 10, "bold")).grid(row=3, column=0, sticky="w", pady=2)
        ttk.Label(header_frame, text=last_state_text, wraplength=800).grid(row=3, column=1, sticky="w", padx=5)
        conversation_frame = ttk.LabelFrame(main_frame, text="Chronologische Konversation aller Systeme", padding=10); conversation_frame.pack(fill="both", expand=True, pady=10)
        log_text = tk.Text(conversation_frame, wrap="word", font=("Courier New", 9))
        scrollbar = ttk.Scrollbar(conversation_frame, orient="vertical", command=log_text.yview)
        log_text.config(yscrollcommand=scrollbar.set); scrollbar.pack(side=tk.RIGHT, fill=tk.Y); log_text.pack(fill="both", expand=True)
        for _, row in incident['data'].iterrows():
            timestamp = row['Timestamp'].strftime('%H:%M:%S.%f')[:-3]; line_to_insert = f"[{timestamp}] [{row['Quelle']:^7s}] {row['Ereignis']}\n"
            log_text.insert(tk.END, line_to_insert)
            if str(error_code) != "N/A" and (f"mfc={error_code}" in row['OriginalLog'] or f"fault_cause={error_code}" in row['OriginalLog']):
                start_index = f"{log_text.index(tk.END)} - {len(line_to_insert)+1}c"; end_index = f"{log_text.index(tk.END)} - 1c"
                log_text.tag_add("error", start_index, end_index)
        log_text.tag_configure("error", background="#FFD2D2", font=("Courier New", 9, "bold")); log_text.config(state="disabled")

    def _create_loading_window(self):
        self.loading_win = tk.Toplevel(self); self.loading_win.title("Ladevorgang"); self.loading_win.geometry("450x150"); self.loading_win.resizable(False, False); self.update_idletasks(); x = self.winfo_screenwidth() // 2 - self.loading_win.winfo_width() // 2; y = self.winfo_screenheight() // 2 - self.loading_win.winfo_height() // 2; self.loading_win.geometry(f"+{x}+{y}"); self.loading_win.transient(self); self.loading_win.grab_set()
        self.loading_label = ttk.Label(self.loading_win, text="Initialisiere...", font=("Helvetica", 10)); self.loading_label.pack(pady=(15, 5), padx=10, anchor="w")
        self.loading_progress_bar = ttk.Progressbar(self.loading_win, orient="horizontal", mode="determinate"); self.loading_progress_bar.pack(fill=tk.X, expand=True, padx=10)
        self.percent_label = ttk.Label(self.loading_win, text="0%", font=("Helvetica", 10)); self.percent_label.pack(pady=5)
        self.incident_counter_label = ttk.Label(self.loading_win, text="", font=("Helvetica", 9)); self.incident_counter_label.pack(pady=2)
    
    def _update_progress(self, current, total, status_text):
        if self.loading_win and self.loading_win.winfo_exists():
            progress = int((current / total) * 100) if total > 0 else 0; self.loading_win.lift()
            self.loading_label.config(text=status_text)
            self.loading_progress_bar['value'] = progress; self.percent_label.config(text=f"{progress}%"); self.loading_win.update_idletasks()
    
    def _update_incident_progress(self, current, total):
        if self.loading_win and self.loading_win.winfo_exists():
            self.incident_counter_label.config(text=f"Fall {current} von {total} analysiert...")
            self.loading_win.update_idletasks()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        root = tk.Tk()
        app = MV3DApp(root)
        root.mainloop()
    except Exception as e:
        with open("mv3d_crash_report.log", "w", encoding='utf-8') as f:
            f.write("Ein kritischer Fehler ist in mv3d_app.py aufgetreten:\n\n")
            f.write(traceback.format_exc())