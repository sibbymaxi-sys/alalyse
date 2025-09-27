# mv3d_app.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import os
import threading
import re
from datetime import timedelta
from base_app import BaseApp
from error_definitions import check_for_error
import config_manager as cfg
from timespan_dialog import TimespanDialog
from log_previewer import preview_log_directory
from ftp_dialog_mv3d import FTPDialogMV3D
from ftp_client import SFTPClient
from sftp_status_window import SFTPStatusWindow

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
        super().__init__(parent, app_name="MV3D System Analyzer", version="6.9 (Final)", *args, **kwargs)
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

        incident_frame = ttk.LabelFrame(main_frame, text="Fall-Akten (kritische Ereignisse)", padding=10)
        incident_frame.pack(fill=tk.BOTH, expand=True, pady=(10,0))
        self.tree = ttk.Treeview(incident_frame, columns=("Timestamp", "Type", "RootCause"), show="headings")
        self.tree.heading("Timestamp", text="Zeitpunkt"); self.tree.column("Timestamp", width=150)
        self.tree.heading("Type", text="Vorfalls-Typ", anchor="center"); self.tree.column("Type", width=120, anchor="center")
        self.tree.heading("RootCause", text="Beschreibung / Ursache"); self.tree.column("RootCause", width=600)
        self.tree.bind("<Double-1>", self._on_incident_select)
        scrollbar = ttk.Scrollbar(incident_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set); scrollbar.pack(side=tk.RIGHT, fill=tk.Y); self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        status_frame = ttk.Frame(main_frame); status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        self.status_label = ttk.Label(status_frame, text="Bereit."); self.status_label.pack(side=tk.LEFT, padx=5)

    def _open_ftp_dialog(self):
        """ Öffnet den spezifischen SFTP-Dialog für MV3D. """
        dialog = FTPDialogMV3D(self)
        sftp_details = dialog.show()
        if sftp_details:
            local_dir = os.path.join(os.getcwd(), "logs", "mv3d")
            status_win = SFTPStatusWindow(self)
            def progress_callback(message, progress=None):
                self.after(0, status_win.update_status, message, progress)
            thread = threading.Thread(target=self._run_sftp_download, args=(sftp_details, local_dir, progress_callback, status_win), daemon=True)
            thread.start()

    def _run_sftp_download(self, details, local_dir, progress_callback, status_win):
        """ Lädt von mehreren IPs/Verzeichnissen für MV3D via SFTP. """
        user = details.get("user"); passwd = details.get("passwd"); targets = details.get("targets", {})
        all_downloaded_files = []; has_errors = False
        
        total_targets = len([t for t in targets.values() if t.get("host") and t.get("path")])
        completed_targets = 0

        for system, info in targets.items():
            host = info.get("host"); remote_path = info.get("path")
            if not host or not remote_path: continue
            
            client = SFTPClient(host, user, passwd)
            message, success = client.connect(progress_callback)
            
            if success:
                message, downloaded = client.download_logs_from_paths({system: remote_path}, local_dir, progress_callback)
                if not downloaded: has_errors = True
                else: all_downloaded_files.extend(downloaded)
            else:
                has_errors = True
            
            client.disconnect()
            completed_targets += 1
            progress = int((completed_targets/total_targets)*100) if total_targets > 0 else 100
            progress_callback(f"System '{system}' abgeschlossen.", progress)
        
        if not all_downloaded_files and has_errors:
             self.after(0, lambda: messagebox.showerror("Download fehlgeschlagen", "Es konnten keine Log-Dateien heruntergeladen werden.", parent=self))
        elif all_downloaded_files:
            self.after(0, self.on_ftp_download_complete, local_dir)

        self.after(0, status_win.close_window)

    def on_ftp_download_complete(self, directory):
        self._process_directory(directory)

    def _load_from_dialog(self):
        config = cfg.load_profiles()
        last_dir = config.get("last_mv3d_dir", os.getcwd())
        dir_path = filedialog.askdirectory(title="Wählen Sie das Haupt-Log-Verzeichnis", initialdir=last_dir)
        if not dir_path: return
        config["last_mv3d_dir"] = dir_path; cfg.save_profiles(config)
        self._process_directory(dir_path)

    def _process_directory(self, dir_path):
        self.status_label.config(text="Scanne Verzeichnis nach verfügbaren Daten..."); self.update_idletasks()
        start_date, end_date, total_entries = preview_log_directory(dir_path, self.parser_map)
        self.status_label.config(text="Bereit.")
        if not start_date and not end_date:
            messagebox.showwarning("Keine Daten", f"Im Verzeichnis '{dir_path}' konnten keine Log-Dateien gefunden werden.", parent=self)
            return
        timespan_dialog = TimespanDialog(self, available_start=start_date, available_end=end_date, total_entries=total_entries)
        time_filter = timespan_dialog.show()
        if not time_filter: return
        self._start_loading_process(dir_path, time_filter)

    def _start_loading_process(self, dir_path, time_filter):
        self._create_loading_window()
        thread = threading.Thread(target=self._load_and_process_files, args=(dir_path, time_filter), daemon=True); thread.start()

    def _load_and_process_files(self, dir_path, time_filter):
        files_to_process = []
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if file in self.parser_map:
                    files_to_process.append((os.path.join(root, file), self.parser_map[file]))
        if not files_to_process: self.after(0, self._finalize_loading, False, f"Im Ordner '{dir_path}' wurden keine bekannten Log-Dateien gefunden."); return
        
        all_dfs = []
        try:
            for i, (path, parser) in enumerate(files_to_process):
                df = parser(path)
                if not df.empty: all_dfs.append(df)
            if not all_dfs: self.after(0, self._finalize_loading, False, "Keine Log-Einträge in den verarbeiteten Dateien gefunden."); return
            
            temp_df = pd.concat(all_dfs).sort_values(by="Timestamp").reset_index(drop=True)
            temp_df['Timestamp'] = pd.to_datetime(temp_df['Timestamp'])

            if not time_filter["load_all"]:
                self.combined_df = temp_df[(temp_df['Timestamp'] >= time_filter['start']) & (temp_df['Timestamp'] <= time_filter['end'])]
            else:
                self.combined_df = temp_df
            if self.combined_df.empty: self.after(0, self._finalize_loading, False, "Keine Log-Einträge im gewählten Zeitraum gefunden."); return
            
            self._identify_incidents_efficiently()
            
            message = f"{len(self.incidents_df)} kritische Ereignisse (Fall-Akten) wurden identifiziert."
            self.after(0, self._finalize_loading, True, message)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Fehler", f"Ein Fehler ist beim Verarbeiten der Dateien aufgetreten:\n{e}", parent=self))
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
        error_rows = self.combined_df[self.combined_df['OriginalLog'].str.contains("ERROR|FAIL|FAULT|overrunCount", case=False, na=False)]
        processed_indices = set()
        
        for index, row in error_rows.iterrows():
            if index in processed_indices: continue
            
            incident_type = "System-Fehler"
            if "overrunCount" in row['OriginalLog']:
                match = re.search(r"overrunCount=(\d+)", row['OriginalLog'])
                if match and int(match.group(1)) > 0:
                    incident_type = "System-Overrun"
                else: continue
            
            error_timestamp = row['Timestamp']
            start_time = error_timestamp - timedelta(seconds=10); end_time = error_timestamp + timedelta(seconds=5)
            incident_df = self.combined_df[(self.combined_df['Timestamp'] >= start_time) & (self.combined_df['Timestamp'] <= end_time)]
            if incident_df.empty: continue

            context_df = self.combined_df[(self.combined_df['Timestamp'] < incident_df['Timestamp'].min())]
            last_scs_opstate = "Unbekannt"; scs_states = context_df[context_df['Ereignis'].str.contains("Betriebs-Status wechselt zu:", na=False)]
            if not scs_states.empty: last_scs_opstate = scs_states.iloc[-1]['Ereignis'].split(': ')[-1]
            last_bhs_state = "Unbekannt"; bhs_states = context_df[context_df['Ereignis'].str.contains("Anlagen-Status:", na=False)]
            if not bhs_states.empty: last_bhs_state = bhs_states.iloc[-1]['Ereignis'].split(': ')[-1].replace("'", "")
            
            root_cause_text = "Overrun-Zähler erhöht." if incident_type == "System-Overrun" else check_for_error(row['OriginalLog'])[0]

            incidents.append({'Timestamp': error_timestamp, 'Type': incident_type, 'RootCause': root_cause_text, 'data': incident_df, 'context': {'scs_opstate': last_scs_opstate, 'bhs_state': last_bhs_state}})
            processed_indices.update(incident_df.index)
        self.incidents_df = pd.DataFrame(incidents)

    def _populate_date_filter(self):
        self.date_filter_combo.set('')
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
            self.tree.insert("", "end", iid=index, values=(row['Timestamp'].strftime('%Y-%m-%d %H:%M:%S'), row['Type'], row['RootCause']))

    def _on_incident_select(self, event):
        selected_item = self.tree.focus();
        if not selected_item: return
        incident_index = int(selected_item); incident = self.incidents_df.loc[incident_index]
        self._show_case_file_window(incident)
        
    def _show_case_file_window(self, incident):
        win = tk.Toplevel(self); win.title(f"Fall-Akte: {incident['Type']} um {incident['Timestamp'].strftime('%H:%M:%S')}"); win.geometry("950x700"); win.transient(self); win.grab_set()
        main_frame = ttk.Frame(win, padding=20); main_frame.pack(fill="both", expand=True)
        header_frame = ttk.LabelFrame(main_frame, text="Vorfalls-Übersicht", padding=10); header_frame.pack(fill="x", expand=True)
        ttk.Label(header_frame, text="Beschreibung:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(header_frame, text=incident['RootCause'], foreground="red").grid(row=0, column=1, sticky="w")
        context_frame = ttk.LabelFrame(main_frame, text="System-Status vor dem Fehler", padding=10); context_frame.pack(fill="x", expand=True, pady=10)
        ttk.Label(context_frame, text="Letzter SCS Betriebs-Status:").grid(row=0, column=0, sticky="w")
        ttk.Label(context_frame, text=incident['context']['scs_opstate']).grid(row=0, column=1, sticky="w")
        ttk.Label(context_frame, text="Letzter BHS Anlagen-Status:").grid(row=1, column=0, sticky="w")
        ttk.Label(context_frame, text=incident['context']['bhs_state']).grid(row=1, column=1, sticky="w")
        conversation_frame = ttk.LabelFrame(main_frame, text="Chronologische Konversation der Systeme", padding=10); conversation_frame.pack(fill="both", expand=True)
        log_text = tk.Text(conversation_frame, wrap="word", font=("Courier New", 9)); scrollbar = ttk.Scrollbar(conversation_frame, orient="vertical", command=log_text.yview); log_text.config(yscrollcommand=scrollbar.set); scrollbar.pack(side=tk.RIGHT, fill=tk.Y); log_text.pack(fill="both", expand=True)
        for _, row in incident['data'].iterrows():
            timestamp = row['Timestamp'].strftime('%H:%M:%S.%f')[:-3]; line_to_insert = f"[{timestamp}] [{row['Quelle']:^7s}] {row['Ereignis']}\n"; log_text.insert(tk.END, line_to_insert)
            if "ERROR" in row['OriginalLog'] or "FAIL" in row['OriginalLog'] or "FAULT" in row['OriginalLog']:
                start_index = f"{log_text.index(tk.END)} - {len(line_to_insert)+1}c"; end_index = f"{log_text.index(tk.END)} - 1c"; log_text.tag_add("error", start_index, end_index)
        log_text.tag_configure("error", background="#FFD2D2", font=("Courier New", 9, "bold")); log_text.config(state="disabled")

    def _create_loading_window(self):
        self.loading_win = tk.Toplevel(self); self.loading_win.title("Ladevorgang"); self.loading_win.geometry("450x130"); self.loading_win.resizable(False, False); self.update_idletasks(); x = self.winfo_screenwidth() // 2 - self.loading_win.winfo_width() // 2; y = self.winfo_screenheight() // 2 - self.loading_win.winfo_height() // 2; self.loading_win.geometry(f"+{x}+{y}"); self.loading_win.transient(self); self.loading_win.grab_set()
        self.loading_label = ttk.Label(self.loading_win, text="Initialisiere...", font=("Helvetica", 10)); self.loading_label.pack(pady=(15, 5), padx=10, anchor="w")
        self.loading_progress_bar = ttk.Progressbar(self.loading_win, orient="horizontal", mode="determinate"); self.loading_progress_bar.pack(fill=tk.X, expand=True, padx=10)
        self.percent_label = ttk.Label(self.loading_win, text="0%", font=("Helvetica", 10)); self.percent_label.pack(pady=5)
    def _update_progress(self, current, total, status_text):
        if self.loading_win and self.loading_win.winfo_exists():
            progress = int((current / total) * 100) if total > 0 else 0; self.loading_win.lift()
            if current < total: self.loading_label.config(text=f"Lese Datei: {status_text} ({current}/{total})")
            else: self.loading_label.config(text=f"Status: {status_text}")
            self.loading_progress_bar['value'] = progress; self.percent_label.config(text=f"{progress}%"); self.loading_win.update_idletasks()