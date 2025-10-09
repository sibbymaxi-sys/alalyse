import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import threading
import os
import re
import sys
import traceback
import sv_ttk
import multiprocessing
from datetime import datetime, timedelta
import shutil
from brava_log_parser import parse_log as parse_brava_log

from gateview_casefile_window import GateViewCasefileWindow

class SystemAnalyzerApp:
    def __init__(self, parent):
        self.parent = parent

        self.parent.title("Eigenständige System-Analyse (ClearScan)")
        self.parent.geometry("1100x700")

        # Sicherer Import und Anwendung des sv_ttk-Themas
        try:
            import sv_ttk
            sv_ttk.set_theme("dark")
        except Exception:
            pass

        style = ttk.Style(self.parent)
        style.map('Treeview', background=[('selected', '#343434')], foreground=[('selected', 'white')])

        self.raw_df = pd.DataFrame()
        self.incidents_df = pd.DataFrame()
        self.scanner_df = pd.DataFrame()
        self.oms_df = pd.DataFrame()
        self.brava_df = pd.DataFrame()
        self.loading_win = None
        self._setup_ui()

    def _setup_ui(self):
        main_frame = ttk.Frame(self.parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=5)

        ttk.Button(control_frame, text="Log-Ordner zur Analyse auswählen", command=self._start_analysis_from_dialog).pack(side=tk.LEFT, padx=5, pady=5)

        ttk.Label(control_frame, text="Nach Datum filtern:").pack(side=tk.LEFT, padx=(20, 5))
        self.date_filter_combo = ttk.Combobox(control_frame, state="readonly", width=15)
        self.date_filter_combo.pack(side=tk.LEFT, padx=5)
        self.date_filter_combo.bind("<<ComboboxSelected>>", self._on_date_filter_select)
        ttk.Button(control_frame, text="Filter zurücksetzen", command=self._reset_date_filter).pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="BRAVA/PLC Log laden", command=self.on_brava_log_laden_button_click).pack(side=tk.LEFT, padx=10)

        log_frame = ttk.LabelFrame(main_frame, text="Gefundene System-Ereignisse", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10,0))
        self.tree = ttk.Treeview(log_frame, columns=("Timestamp", "SourceFile", "Error"), show="headings")
        self.tree.heading("Timestamp", text="Zeitpunkt"); self.tree.column("Timestamp", width=150)
        self.tree.heading("SourceFile", text="Quelldatei", anchor="w"); self.tree.column("SourceFile", width=150, anchor="w")
        self.tree.heading("Error", text="Fehlermeldung"); self.tree.column("Error", width=700)
        self.tree.bind("<Double-1>", self._on_item_select)

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.tag_configure("error", background="#4B2525")
        self.tree.tag_configure("restart", foreground="#6495ED")

        status_bar = ttk.Frame(self.parent, padding=(5, 2)); status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = ttk.Label(status_bar, text="Bereit."); self.status_label.pack(side=tk.LEFT, padx=5)






    def lade_und_analyse_brava_log(self, file_path):
        return parse_brava_log(file_path)

    def journey_analyse(self):
        all_df = pd.concat([self.scanner_df, self.oms_df, self.brava_df], ignore_index=True)
        journeys = {}
        if not all_df.empty and 'TrayID' in all_df.columns:
            for tray_id in all_df['TrayID'].unique():
                journey_entries = all_df[all_df['TrayID'] == tray_id].sort_values('Timestamp')
                journeys[tray_id] = journey_entries
        return journeys

    def on_brava_log_laden_button_click(self):
        file_path = filedialog.askopenfilename(title="Wählen Sie die BRAVA/PLC Logdatei")
        if not file_path:
            return
        self.brava_df = self.lade_und_analyse_brava_log(file_path)
        self.update_journeys()

    def update_journeys(self):
        journeys = self.journey_analyse()
        # Treeview mit allen Einträgen aktualisieren
        all_df = pd.concat([self.scanner_df, self.oms_df, self.brava_df], ignore_index=True)
        if not all_df.empty and 'Timestamp' in all_df.columns:
            self.incidents_df = all_df.sort_values(by="Timestamp", na_position='first').reset_index(drop=True)
            self._update_treeview()
            self._populate_date_filter()
            self.status_label.config(text=f"{len(self.incidents_df)} relevante Ereignisse gefunden.")

    def _start_analysis_from_dialog(self):
        dir_path = filedialog.askdirectory(title="Wählen Sie den Log-Ordner zur System-Analyse")
        if not dir_path: return
        self._create_loading_window()
        thread = threading.Thread(target=self._run_analysis_thread, args=(dir_path,), daemon=True)
        thread.start()

    def _run_analysis_thread(self, dir_path):
        def progress_callback(progress, message): self.parent.after(0, self._update_progress, progress, message)

        files_to_exclude = ['yum.log', 'oms.log', 'scanner_bag.log', 'app.log']
        log_files = []
        progress_callback(0, "Suche nach relevanten Log-Dateien...")

        for root, _, files in os.walk(dir_path):
            for file in files:
                filename_lower = file.lower()
                if filename_lower in files_to_exclude or filename_lower.startswith('alg'):
                    continue
                if filename_lower.endswith('.log'):
                    file_path = os.path.join(root, file)
                    log_files.append(file_path)

        if not log_files:
            self.parent.after(0, self._finalize_analysis, False, "Keine relevanten .log-Dateien gefunden.")
            return

        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            dest_dir = os.path.join("logs", "gatview_download", f"tec_{today_str}")
            os.makedirs(dest_dir, exist_ok=True)
            progress_callback(0, "Kopiere gefundene Log-Dateien...")
            for src_path in log_files: shutil.copy(src_path, dest_dir)
            progress_callback(0, f"{len(log_files)} Dateien nach '{dest_dir}' kopiert.")
        except Exception as e:
            self.parent.after(0, self._finalize_analysis, False, f"Fehler beim Kopieren der Dateien: {e}")
            return

        year = str(datetime.now().year)

        all_entries = []
        for i, file_path in enumerate(log_files):
            filename = os.path.basename(file_path)
            progress_callback(int(((i + 1) / len(log_files)) * 100), f"Lese: {filename}")

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        timestamp = self._parse_timestamp(line, year)
                        all_entries.append({'Timestamp': timestamp, 'SourceFile': filename, 'OriginalLog': line.strip()})
            except Exception as e:
                print(f"FEHLER beim Lesen/Parsen der Datei {filename}: {e}")

        if not all_entries:
            self.parent.after(0, self._finalize_analysis, False, "Keine lesbaren Einträge gefunden.")
            return

        self.raw_df = pd.DataFrame(all_entries).sort_values(by="Timestamp", na_position='first').reset_index(drop=True)
        event_pattern = r"(?:ERROR|FAIL|FAULT|WARNING|Restarting Script)"
        error_mask = self.raw_df['OriginalLog'].str.contains(event_pattern, case=False, na=False)
        self.incidents_df = self.raw_df[error_mask].copy()
        self.parent.after(0, self._finalize_analysis, True, f"{len(self.incidents_df)} relevante Ereignisse gefunden.")

    def _parse_timestamp(self, line, year):
        match1 = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[\.,]\d{3})', line)
        if match1:
            try:
                return pd.to_datetime(match1.group(1), errors='coerce')
            except ValueError:
                pass

        match2 = re.search(r'(\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}[\.,]\d{3}\s+\d{4})', line)
        if match2:
            try:
                return datetime.strptime(match2.group(1), '%a %b %d %H:%M:%S.%f %Y')
            except ValueError:
                try:
                    return datetime.strptime(match2.group(1), '%a %b %d %H:%M:%S %Y')
                except ValueError:
                    pass

        match3 = re.search(r'(\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}[\.,]\d{3})', line)
        if match3:
            try:
                return pd.to_datetime(f"{match3.group(1)} {year}", format='%a %b %d %H:%M:%S.%f %Y', errors='coerce')
            except Exception:
                pass

        match4 = re.search(r'(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
        if match4:
            try:
                return pd.to_datetime(f"{year}-{match4.group(1)}", format='%Y-%m-%d %H:%M:%S', errors='coerce')
            except Exception:
                pass

        return None

    def _finalize_analysis(self, success, message):
        if self.loading_win: self.loading_win.destroy(); self.loading_win = None
        if not success:
            messagebox.showwarning("Analyse fehlgeschlagen", message, parent=self.parent)
            return
        self._update_treeview()
        self._populate_date_filter()
        self.status_label.config(text=message)
        messagebox.showinfo("System-Analyse abgeschlossen", message, parent=self.parent)

    def _populate_date_filter(self):
        self.date_filter_combo.set('')
        if self.incidents_df.empty or 'Timestamp' not in self.incidents_df.columns:
            self.date_filter_combo['values'] = []; return
        valid_dates = self.incidents_df['Timestamp'].dropna()
        if not valid_dates.empty:
            unique_dates = sorted(valid_dates.dt.date.unique())
            self.date_filter_combo['values'] = [d.strftime('%Y-%m-%d') for d in unique_dates]

    def _on_date_filter_select(self, event=None):
        selected_date_str = self.date_filter_combo.get()
        if not selected_date_str: return
        selected_date = pd.to_datetime(selected_date_str).date()
        filtered_df = self.incidents_df[self.incidents_df['Timestamp'].dt.date == selected_date]
        self._update_treeview(filtered_df)

    def _reset_date_filter(self):
        self.date_filter_combo.set(''); self._update_treeview()

    def _update_treeview(self, df=None):
        df_to_show = self.incidents_df if df is None else df
        for i in self.tree.get_children(): self.tree.delete(i)
        error_pattern = r"(?:ERROR|FAIL|FAULT|WARNING|Restarting Script)"
        restart_pattern = r"Restarting Script"
        for index, row in df_to_show.iterrows():
            tags = []; log_text = row['OriginalLog']
            if re.search(restart_pattern, log_text, re.IGNORECASE): tags.append("restart")
            elif re.search(error_pattern, log_text, re.IGNORECASE): tags.append("error")
            self.tree.insert("", "end", iid=index, tags=tuple(tags), values=(
                row['Timestamp'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['Timestamp']) else 'N/A',
                row.get('SourceFile', row.get('Quelle', 'N/A')), log_text))

    def _on_item_select(self, event):
        selected_item = self.tree.focus()
        if not selected_item: return
        row_index = int(selected_item)
        selected_row = self.raw_df.loc[row_index]
        GateViewCasefileWindow(self.parent, selected_row, self.raw_df)

    def _create_loading_window(self):
        self.loading_win = tk.Toplevel(self.parent); self.loading_win.title("Ladevorgang"); self.loading_win.geometry("450x130"); self.loading_win.resizable(False, False); self.parent.update_idletasks(); x = self.parent.winfo_screenwidth() // 2 - self.loading_win.winfo_width() // 2; y = self.parent.winfo_screenheight() // 2 - self.loading_win.winfo_height() // 2; self.loading_win.geometry(f"+{x}+{y}"); self.loading_win.transient(self.parent); self.loading_win.grab_set(); self.loading_label = ttk.Label(self.loading_win, text="Initialisiere...", font=("Helvetica", 10)); self.loading_label.pack(pady=(15, 5), padx=10, anchor="w"); self.loading_progress_bar = ttk.Progressbar(self.loading_win, orient="horizontal", mode="determinate"); self.loading_progress_bar.pack(fill=tk.X, expand=True, padx=10); self.percent_label = ttk.Label(self.loading_win, text="0%", font=("Helvetica", 10)); self.percent_label.pack(pady=5)
    def _update_progress(self, progress, filename):
        if self.loading_win: self.loading_win.lift(); self.loading_label.config(text=f"Verarbeite: {filename}"); self.loading_progress_bar['value'] = progress; self.percent_label.config(text=f"{progress}%"); self.loading_win.update_idletasks()