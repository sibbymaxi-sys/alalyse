# gateview_app.py
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import pandas as pd
import threading
import os
import re
import sys
from datetime import datetime, date
import traceback
import multiprocessing
import subprocess

# Imports für die Diagramme
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Import der Parser
from brava_log_parser import parse_log as parse_brava_log
from plc_log_parser import parse_log as parse_plc_log

try:
    import sv_ttk
    from tkcalendar import DateEntry
    from log_parser import parse_log_file
    from data_processor import consolidate_journeys
    from advanced_search_dialog import AdvancedSearchDialog
    from base_app import BaseApp
    import config_manager as cfg
    from ftp_client import SFTPClient
    from ftp_dialog_advanced import AdvancedFTPDialog
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
    sys.exit(1)

class GateViewApp(BaseApp):
    def __init__(self, parent, *args, **kwargs):
        APP_VERSION = "1.3.1" # Version erhöht für Bugfixes
        super().__init__(parent, app_name="GateView Analyzer", version=APP_VERSION, *args, **kwargs)
        self.raw_df = pd.DataFrame()
        self.journeys_df = pd.DataFrame()
        self.loading_win = None
        self._setup_ui()

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding="10"); main_frame.pack(fill=tk.BOTH, expand=True)
        button_frame = ttk.Frame(main_frame); button_frame.pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="1. Scanner-Log öffnen", command=lambda: self._load_from_dialog(mode="scanner")).pack(side=tk.LEFT, padx=5)
        self.oms_button = ttk.Button(button_frame, text="2. OMS-Log hinzufügen", command=lambda: self._load_from_dialog(mode="oms"), state="disabled"); self.oms_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Logs laden (Lokal/FTP)", command=self._run_brava_trs_download, style='Accent.TButton').pack(side=tk.LEFT, padx=15)
        self.stats_button = ttk.Button(button_frame, text="Durchsatz-Statistik", command=self._show_throughput_statistics, state="disabled"); self.stats_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="System-Analyse", command=self._launch_system_analyzer).pack(side=tk.LEFT, padx=15)
        self.search_button = ttk.Button(button_frame, text="Erweiterte Suche", command=self._open_advanced_search); self.search_button.pack(side=tk.LEFT, padx=5)
        filter_frame = ttk.Frame(main_frame, padding=(0, 5)); filter_frame.pack(fill=tk.X, pady=(10,0))
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5)); ttk.Label(filter_frame, text="BagID:").pack(side=tk.LEFT, padx=(10, 5)); self.bag_id_filter = ttk.Combobox(filter_frame, width=15); self.bag_id_filter.pack(side=tk.LEFT); ttk.Label(filter_frame, text="IATA:").pack(side=tk.LEFT, padx=(10, 5)); self.iata_filter = ttk.Combobox(filter_frame, width=10); self.iata_filter.pack(side=tk.LEFT)
        ttk.Button(filter_frame, text="Anwenden", command=self._apply_filters).pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="Zurücksetzen", command=self._reset_filters).pack(side=tk.LEFT, padx=5)
        tree_frame = ttk.Frame(main_frame); tree_frame.pack(fill=tk.BOTH, expand=True, pady=(5,0))
        self.tree = ttk.Treeview(tree_frame); scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set); scrollbar.pack(side=tk.RIGHT, fill=tk.Y); self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); self.tree.bind("<Double-1>", self._on_item_double_click)
        self.status_label = ttk.Label(self.status_bar, text="Bereit."); self.status_label.pack(side=tk.LEFT, padx=5)

    def _add_bar_labels(self, ax):
        for bar in ax.patches:
            y_value = bar.get_height()
            x_value = bar.get_x() + bar.get_width() / 2
            label = f"{int(y_value)}"
            if y_value > 0:
                ax.annotate(label, (x_value, y_value), xytext=(0, 5), textcoords="offset points", ha='center', va='bottom', fontsize=8)

    def _show_throughput_statistics(self):
        if self.journeys_df.empty or 'Timestamp' not in self.journeys_df.columns:
            messagebox.showinfo("Keine Daten", "Keine gültigen Daten für die Statistik vorhanden.", parent=self)
            return
        stats_win = tk.Toplevel(self); stats_win.title("Durchsatz-Statistik"); stats_win.geometry("800x900")
        df = self.journeys_df.copy(); df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce'); df.dropna(subset=['Timestamp'], inplace=True)
        if df.empty:
            messagebox.showinfo("Keine Daten", "Keine gültigen Zeitstempel für die Statistik gefunden.", parent=self)
            stats_win.destroy(); return
        
        hourly = df.groupby(df['Timestamp'].dt.hour).size().rename_axis("Stunde").reset_index(name='Anzahl')
        daily = df.groupby(df['Timestamp'].dt.date).size().rename_axis("Datum").reset_index(name='Anzahl')
        monthly = df.groupby(df['Timestamp'].dt.to_period('M')).size().rename_axis("Monat").reset_index(name='Anzahl'); monthly['Monat'] = monthly['Monat'].astype(str)
        
        notebook = ttk.Notebook(stats_win); notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def create_tab(parent, title, data_df):
            tab_frame = ttk.Frame(parent); notebook.add(tab_frame, text=title)
            table_frame = ttk.LabelFrame(tab_frame, text="Zahlen", padding=10); table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            tree = ttk.Treeview(table_frame, columns=list(data_df.columns), show="headings")
            for col in data_df.columns: tree.heading(col, text=col); tree.column(col, width=100, anchor="center")
            for _, row in data_df.iterrows(): tree.insert("", "end", values=list(row))
            tree.pack(fill=tk.BOTH, expand=True)
            chart_frame = ttk.LabelFrame(tab_frame, text="Grafik", padding=10); chart_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
            fig = Figure(figsize=(4, 2.5), dpi=100); ax = fig.add_subplot(111)
            plot_df = data_df.set_index(data_df.columns[0])
            plot_df.plot(kind='bar', ax=ax, legend=False); ax.set_ylabel("Anzahl"); ax.set_xlabel(""); ax.tick_params(axis='x', rotation=45, labelsize=8)
            self._add_bar_labels(ax); fig.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=chart_frame); canvas.draw(); canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        create_tab(notebook, "Stündlich", hourly)
        create_tab(notebook, "Täglich", daily)
        create_tab(notebook, "Monatlich", monthly)

    def _launch_system_analyzer(self):
        new_window = tk.Toplevel(self); new_window.title("Eigenständige System-Analyse (ClearScan)"); new_window.geometry("1100x700"); SystemAnalyzerApp(new_window)
    
    def _show_help_window(self):
        help_win = tk.Toplevel(self); help_win.title("Anleitung - GateView Analyzer"); help_win.geometry("800x600"); help_win.transient(self); help_win.grab_set()
        text_area = scrolledtext.ScrolledText(help_win, wrap=tk.WORD, font=("Helvetica", 10), padx=10, pady=10); text_area.pack(expand=True, fill=tk.BOTH)
        text_area.insert(tk.INSERT, GATEVIEW_HELP_TEXT); text_area.config(state="disabled")

    def _open_ftp_dialog(self):
        dialog = AdvancedFTPDialog(self, app_name="gateview"); ftp_details = dialog.show()
        if ftp_details:
            log_win = SFTPLogWindow(self)
            thread = threading.Thread(target=self._run_sftp_download, args=(ftp_details, log_win), daemon=True); thread.start()

    def _run_sftp_download(self, profile, log_win):
        if getattr(sys, 'frozen', False): application_path = os.path.dirname(sys.executable)
        else: application_path = os.path.dirname(os.path.abspath(__file__))
        today_str = date.today().strftime("%Y-%m-%d"); local_dir = os.path.join(application_path, "Gateview", today_str)
        os.makedirs(local_dir, exist_ok=True)
        targets = profile.get("targets", {}); all_downloaded_files, has_errors = [], False
        def log_callback(message): self.after(0, log_win.log, message)
        for system_name, details in targets.items():
            host = details.get("host");
            if not host: continue
            log_callback(f"--- Starte Verbindung zu {system_name} ({host}) ---")
            client = SFTPClient(host, details.get("user"), details.get("passwd"), details.get("port", "22"))
            _, success = client.connect(log_callback)
            if success:
                log_callback(f"Erfolgreich mit {system_name} verbunden.")
                rules = details.get("download_rules")
                if rules:
                    _, downloaded = client.execute_download_rules(rules, local_dir, log_callback)
                    if downloaded: all_downloaded_files.extend(downloaded)
                else:
                    log_callback("-> Info: Kein 'download_rules' im Profil gefunden. Nutze Standard-Methode.")
                    path_list = details.get("paths", [])
                    for path in path_list:
                        if path.endswith('/'):
                            _, downloaded = client.download_all_files_from_dir(path, local_dir, log_callback)
                            if downloaded: all_downloaded_files.extend(downloaded)
                        else:
                            _, downloaded_path = client.download_single_file(path, local_dir, log_callback)
                            if downloaded_path: all_downloaded_files.append(downloaded_path)
            else:
                has_errors = True; log_callback(f"FEHLER bei der Verbindung zu {system_name}.")
            log_callback(f"--- Trenne Verbindung zu {system_name} ---"); client.disconnect()
        if all_downloaded_files:
            log_callback(f"Download von {len(all_downloaded_files)} Datei(en) abgeschlossen. Starte Analyse...")
            self.after(0, self.on_ftp_download_complete, all_downloaded_files)
        elif has_errors: log_callback("Download-Prozess mit Fehlern abgeschlossen, keine Dateien geladen.")
        else: log_callback("Prozess beendet. Keine Zieldateien konnten gefunden werden.")
        self.after(4000, log_win.close_window)

    def _run_brava_trs_download(self):
        auswahl = messagebox.askquestion("Logs laden", "Möchtest du die Log-Dateien per FTP laden?\n\nWähle 'Ja' für FTP oder 'Nein' für eine lokale Datei.", icon='question')
        if auswahl == 'yes': self._open_ftp_dialog()
        else:
            file_paths = filedialog.askopenfilenames(title="Wähle lokale Log-Dateien", filetypes=(("Log- und CSV-Dateien", "*.log *.csv"), ("Alle Dateien", "*.*")))
            if not file_paths: return
            self._start_loading_process(list(file_paths))

    def on_ftp_download_complete(self, downloaded_files):
        messagebox.showinfo("Download Abgeschlossen", f"{len(downloaded_files)} Datei(en) heruntergeladen.\nAnalyse wird gestartet.", parent=self)
        self.raw_df = pd.DataFrame(); self._start_loading_process(downloaded_files)

    def _start_loading_process(self, file_paths):
        self._create_loading_window()
        thread = threading.Thread(target=self._load_and_process_files, args=(file_paths,), daemon=True)
        thread.start(); self.after(100, self._check_thread, thread)

    def _load_from_dialog(self, mode):
        config = cfg.load_config()
        last_dir = config.get("last_gateview_dir", os.getcwd())
        file_types = (("Log- und CSV-Dateien", "*.log *.csv"), ("Alle Dateien", "*.*"))
        file_path = filedialog.askopenfilename(title=f"{mode.upper()}-Log auswählen", initialdir=last_dir, filetypes=file_types)
        if not file_path: return
        config["last_gateview_dir"] = os.path.dirname(file_path); cfg.save_config(config)
        if mode == "scanner": self.raw_df = pd.DataFrame()
        self._start_loading_process([file_path])

    def _open_advanced_search(self):
        dialog = AdvancedSearchDialog(self); criteria = dialog.show()
        if criteria: self._perform_advanced_search(criteria)

    def _perform_advanced_search(self, criteria):
        df = self.journeys_df.copy()
        if criteria['bag_id']: df = df[df['BagID'].str.contains(criteria['bag_id'], case=False, na=False)]
        if criteria['iata']: df = df[df['IATA'].str.contains(criteria['iata'], case=False, na=False)]
        try:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            start_date_str, end_date_str = criteria['start_date'], criteria['end_date']
            if start_date_str and end_date_str:
                start_month, start_day = map(int, start_date_str.split('-')); end_month, end_day = map(int, end_date_str.split('-'))
                start_tuple, end_tuple = (start_month, start_day), (end_month, end_day)
                df_dates = df['Timestamp'].dt.strftime('%m-%d').str.split('-').apply(lambda x: (int(x[0]), int(x[1])))
                if start_tuple <= end_tuple: df = df[df_dates.between(start_tuple, end_tuple, inclusive="both")]
                else: df = df[(df_dates >= start_tuple) | (df_dates <= end_tuple)]
        except Exception as e: messagebox.showerror("Ungültiges Datum", f"Fehler bei der Datumsverarbeitung: {e}"); return
        if criteria['oms_only']:
            oms_bag_ids = self.raw_df[self.raw_df['Source'] == 'OMS']['BagID'].unique()
            df = df[df['BagID'].isin(oms_bag_ids)]
        self._update_treeview(df); self.status_label.config(text=f"{len(df)} Einträge nach erweiterter Suche gefunden.")

    def _create_loading_window(self):
        self.loading_win = tk.Toplevel(self); self.loading_win.title("Ladevorgang"); self.loading_win.geometry("450x130"); self.loading_win.resizable(False, False); self.update_idletasks(); x, y = (self.winfo_screenwidth()//2-self.loading_win.winfo_width()//2), (self.winfo_screenheight()//2-self.loading_win.winfo_height()//2); self.loading_win.geometry(f"+{x}+{y}"); self.loading_win.transient(self); self.loading_win.grab_set(); self.loading_label = ttk.Label(self.loading_win, text="Initialisiere...", font=("Helvetica", 10)); self.loading_label.pack(pady=(15, 5), padx=10, anchor="w"); self.loading_progress_bar = ttk.Progressbar(self.loading_win, orient="horizontal", mode="determinate"); self.loading_progress_bar.pack(fill=tk.X, expand=True, padx=10); self.percent_label = ttk.Label(self.loading_win, text="0%", font=("Helvetica", 10)); self.percent_label.pack(pady=5)

    def _update_progress(self, progress, filename):
        if self.loading_win: self.loading_win.lift(); self.loading_label.config(text=f"Verarbeite: {filename}"); self.loading_progress_bar['value'] = progress; self.percent_label.config(text=f"{progress}%"); self.loading_win.update_idletasks()

    def _check_thread(self, thread):
        if thread.is_alive(): self.after(100, self._check_thread, thread)
        else: self.after(100, self._finalize_loading)

    def _load_and_process_files(self, file_paths):
        for file_path in file_paths:
            filename = os.path.basename(file_path).lower()
            new_df = parse_log_file(file_path, lambda p, f: self.after(0, self._update_progress, p, f))
            if new_df is not None and not new_df.empty:
                self.raw_df = pd.concat([self.raw_df, new_df]).drop_duplicates().sort_values(by="Timestamp").reset_index(drop=True)
        
        self.journeys_df = consolidate_journeys(self.raw_df)
        if 'Source' in self.raw_df.columns and 'BagID' in self.raw_df.columns:
            source_info_map = self.raw_df[self.raw_df['Source'].str.upper().isin(['OMS', 'PLC'])].groupby('BagID')['Source'].unique().apply(lambda x: ', '.join(sorted(x))).reset_index(name='Datenquellen')
            if not source_info_map.empty:
                self.journeys_df = pd.merge(self.journeys_df, source_info_map, on='BagID', how='left')
                self.journeys_df['Datenquellen'].fillna('', inplace=True)
            else: self.journeys_df['Datenquellen'] = ''
        else: self.journeys_df['Datenquellen'] = ''

    def _finalize_loading(self):
        if self.loading_win: self.loading_win.destroy(); self.loading_win = None
        self.after(0, lambda: (self.oms_button.config(state="normal"), self.stats_button.config(state="normal")))
        self._update_gui_after_load()

    def _update_gui_after_load(self):
        self._populate_filters(); self._reset_filters()
        self.status_label.config(text=f"{len(self.journeys_df)} Gepäck-Durchläufe gefunden.")
        messagebox.showinfo("Erfolg", f"Analyse abgeschlossen. {len(self.journeys_df)} einzigartige Gepäck-Durchläufe gefunden.")

    def _populate_filters(self):
        if not self.journeys_df.empty:
            self.bag_id_filter['values'] = sorted(self.journeys_df['BagID'].dropna().unique())
            self.iata_filter['values'] = sorted(self.journeys_df['IATA'].dropna().unique())

    def _apply_filters(self, event=None):
        df_to_show = self.journeys_df.copy()
        bag_id_val, iata_val = self.bag_id_filter.get(), self.iata_filter.get()
        if bag_id_val: df_to_show = df_to_show[df_to_show['BagID'] == bag_id_val]
        if iata_val: df_to_show = df_to_show[df_to_show['IATA'] == iata_val]
        self._update_treeview(df_to_show)

    def _reset_filters(self):
        self.bag_id_filter.set(''); self.iata_filter.set(''); self._update_treeview(self.journeys_df)

    def _update_treeview(self, df):
        for i in self.tree.get_children(): self.tree.delete(i)
        
        cols = list(df.columns)
        if 'Datenquellen' in cols:
            cols.remove('Datenquellen'); cols.insert(2 if 'IATA' in cols else 1, 'Datenquellen')
        
        self.tree["columns"] = cols; self.tree["show"] = "headings"
        for col in cols: self.tree.heading(col, text=col)

        if "Datenquellen" in cols: self.tree.column("Datenquellen", width=100, anchor='center')
        if "Operator" in cols: self.tree.column("Operator", width=80, anchor='center')
        
        for index, row in df.iterrows(): self.tree.insert("", "end", values=list(row[cols]), iid=index)

    def _on_item_double_click(self, event):
        try:
            item_id = self.tree.identify_row(event.y)
            if not item_id: return
            item_values = self.tree.item(item_id, "values")
            try:
                bag_id_column_index = list(self.tree["columns"]).index('BagID')
            except ValueError:
                messagebox.showerror("Fehler", "Spalte 'BagID' nicht gefunden."); return
            bag_id_to_find = item_values[bag_id_column_index]
            if not bag_id_to_find:
                messagebox.showwarning("Info", "Keine BagID in dieser Zeile."); return
            self._show_bag_history_window(str(bag_id_to_find))
        except Exception:
            messagebox.showerror("Unerwarteter Fehler", f"Fehler beim Öffnen der Details:\n\n{traceback.format_exc()}")
    
    def _extract_routing_info(self, history_df):
        info = {'iata': 'N/A', 'machine_decision': 'N/A', 'operator_decision': 'N/A', 'final_command': 'N/A', 'operator': 'N/A'}
        if history_df.empty: return info
        valid_iatas = history_df['IATA'][(history_df['IATA'].notna()) & (~history_df['IATA'].isin(['N/A', 'NO_READ']))]
        if not valid_iatas.empty: info['iata'] = valid_iatas.iloc[0]
        patterns = {'machine_decision': r"Maschinelle Entscheidung.*:\s*(.+)",'operator_decision': r"Finale Operator-Entscheidung.*:\s*(.+)",'final_command': r"Finaler Befehl an Förderanlage gesendet: (.+)"}
        for key, pattern in patterns.items():
            matches = history_df['Klartext'].str.extract(pattern, flags=re.IGNORECASE, expand=False).dropna()
            if not matches.empty: info[key] = matches.iloc[-1].replace("**", "")
        brava_cmd = history_df[(history_df['Source'] == 'BRAVA') & (history_df['Klartext'].str.contains("Finaler Befehl an PLC", na=False))]
        if not brava_cmd.empty:
            match = re.search(r"Finaler Befehl an PLC:\s*(.+)", brava_cmd.iloc[-1]['Klartext'])
            if match: info['final_command'] = match.group(1)
        if 'Operator' in history_df.columns:
            valid_operators = history_df['Operator'].dropna()
            if not valid_operators.empty: info['operator'] = valid_operators.iloc[-1]
        return info

    def _show_bag_history_window(self, bag_id):
        win = tk.Toplevel(self); win.title(f"Detail-Analyse für BagID: {bag_id}"); win.geometry("1100x800")
        history_df = self.raw_df[self.raw_df['BagID'] == bag_id].sort_values(by="Timestamp")
        routing_info = self._extract_routing_info(history_df)
        summary_frame = ttk.LabelFrame(win, text="Analyse-Ergebnis", padding=10); summary_frame.pack(fill=tk.X, padx=10, pady=10)
        labels = {"IATA:": 'iata', "Maschinen-Entscheid:": 'machine_decision', "Operator-Entscheid:": 'operator_decision', "Finaler Operator:": 'operator', "Finaler Befehl an PLC:": 'final_command'}
        for i, (label, key) in enumerate(labels.items()):
            ttk.Label(summary_frame, text=label, font=("Helvetica", 10, "bold")).grid(row=i, column=0, sticky="w")
            ttk.Label(summary_frame, text=routing_info[key]).grid(row=i, column=1, sticky="w", padx=5)
        notebook = ttk.Notebook(win); notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        tabs = {"Klartext-Analyse": tk.Text(notebook, wrap=tk.WORD, font=("Courier New", 10)), "Scanner-Log": tk.Text(notebook, wrap=tk.WORD, font=("Courier New", 9)), "OMS-Log": tk.Text(notebook, wrap=tk.WORD, font=("Courier New", 9)), "PLC-Log": tk.Text(notebook, wrap=tk.WORD, font=("Courier New", 9))}
        for name, text_widget in tabs.items(): notebook.add(text_widget, text=name)
        export_content = self._build_export_content(history_df, bag_id, routing_info)
        if not history_df.empty:
            unique_klartext = history_df[history_df['Klartext'].notna() & (history_df['Klartext'] != history_df['Klartext'].shift())]
            header = f"Chronologische Analyse für BagID: {bag_id} (Wanne: {routing_info['iata']})\n{'=' * 80}\n\n"
            tabs["Klartext-Analyse"].insert(tk.END, header)
            for _, row in unique_klartext.iterrows():
                full_iata = f" ({row.get('IATA_volĺständig')})" if pd.notna(row.get('IATA_volĺständig')) else ""
                tabs["Klartext-Analyse"].insert(tk.END, f"[{row['Timestamp'].strftime('%H:%M:%S.%f')[:-3]}] {row['Klartext']}{full_iata}\n".replace("**", ""))
            for source, widget in [("Scanner", tabs["Scanner-Log"]), ("OMS", tabs["OMS-Log"]), ("PLC", tabs["PLC-Log"])]:
                log_df = history_df[history_df['Source'].str.contains(source, case=False, na=False)]
                if not log_df.empty:
                    widget.insert(tk.END, f"--- Alle {source}-Einträge für BagID {bag_id} ---\n\n")
                    for _, row in log_df.iterrows():
                        widget.insert(tk.END, f"[{row['Timestamp'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] {row['OriginalLog']}\n")
                else:
                    widget.insert(tk.END, f"Keine {source}-Einträge für BagID {bag_id} gefunden.")
        else:
            for widget in tabs.values(): widget.insert(tk.END, f"Keine Detail-Einträge für BagID {bag_id} gefunden.")
        for widget in tabs.values(): widget.config(state=tk.DISABLED)
        ttk.Button(win, text="Analyse speichern...", command=lambda: self._save_analysis(bag_id, routing_info['iata'], export_content)).pack(pady=10)

    def _build_export_content(self, history_df, bag_id, routing_info):
        if history_df.empty: return f"Keine Detail-Einträge für BagID {bag_id} gefunden."
        parts = [f"ANALYSE-REPORT FÜR BAGID {bag_id} (WANNE: {routing_info['iata']})", f"Erstellt am: {datetime.now().strftime('%d.%m.%Y um %H:%M:%S Uhr')}", "="*80, "\n--- ROUTING-ANALYSE ---"]
        parts.extend([f"IATA: {routing_info['iata']}", f"Maschinen-Entscheid: {routing_info['machine_decision']}", f"Operator-Entscheid: {routing_info['operator_decision']}", f"Finaler Operator: {routing_info['operator']}", f"Finaler Befehl an PLC: {routing_info['final_command']}\n", "--- KLARTEXT-ANALYSE ---"])
        unique_klartext = history_df[history_df['Klartext'].notna() & (history_df['Klartext'] != history_df['Klartext'].shift())]
        for _, row in unique_klartext.iterrows():
            full_iata = f" ({row.get('IATA_volĺständig')})" if pd.notna(row.get('IATA_volĺständig')) else ""
            parts.append(f"[{row['Timestamp'].strftime('%H:%M:%S.%f')[:-3]}] {row['Klartext'].replace('**', '')}{full_iata}")
        for source in ["Scanner", "OMS", "PLC"]:
            parts.append(f"\n--- {source.upper()}-LOG AUSZUG ---")
            log_df = history_df[history_df['Source'].str.contains(source, case=False, na=False)]
            if not log_df.empty: parts.extend(log_df['OriginalLog'].tolist())
            else: parts.append(f"Keine {source}-Logs für diesen Durchlauf gefunden.")
        return "\n".join(parts)

    def _save_analysis(self, bag_id, iata, content):
        file_path = filedialog.asksaveasfilename(initialfile=f"Analyse_{bag_id or 'ID'}_{iata or 'IATA'}", defaultextension=".txt", filetypes=[("Textdateien", "*.txt"), ("PDF-Dokumente", "*.pdf")])
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
            styles, story = getSampleStyleSheet(), []
            code_style = styles['Code']; code_style.alignment = TA_LEFT
            content_with_breaks = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('\n', '<br/>\n')
            story.append(Paragraph(content_with_breaks, code_style))
            doc.build(story)
            messagebox.showinfo("Erfolg", f"PDF erfolgreich gespeichert unter:\n{path}")
        except Exception as e: messagebox.showerror("Fehler beim PDF-Export", f"PDF konnte nicht erstellt werden:\n{e}")

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