# gateview_app.py
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import pandas as pd
import threading
import os
import re
from datetime import datetime
import sv_ttk
from tkcalendar import DateEntry
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT
from log_parser import parse_log_file
from data_processor import consolidate_journeys
from advanced_search_dialog import AdvancedSearchDialog
from base_app import BaseApp
import config_manager as cfg
from ftp_dialog_gateview import FTPDialogGateView
from ftp_client import SFTPClient
from sftp_status_window import SFTPStatusWindow
from help_texts import GATEVIEW_HELP_TEXT

class GateViewApp(BaseApp):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, app_name="GateView Analyzer", version="7.23 (Final)", *args, **kwargs)
        self.raw_df = pd.DataFrame()
        self.journeys_df = pd.DataFrame()
        self.loading_win = None
        self._setup_ui()

    def _show_help_window(self):
        """ Zeigt das Hilfe-Fenster für den GateView Analyzer an. """
        help_win = tk.Toplevel(self); help_win.title("Anleitung - GateView Analyzer"); help_win.geometry("800x600")
        help_win.transient(self); help_win.grab_set()
        
        text_area = scrolledtext.ScrolledText(help_win, wrap=tk.WORD, font=("Helvetica", 10), padx=10, pady=10)
        text_area.pack(expand=True, fill=tk.BOTH)
        
        text_area.insert(tk.INSERT, GATEVIEW_HELP_TEXT)
        text_area.config(state="disabled")
    
    # ... (Rest der Datei bleibt unverändert)
    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding="10"); main_frame.pack(fill=tk.BOTH, expand=True); button_frame = ttk.Frame(main_frame); button_frame.pack(fill=tk.X, pady=5); ttk.Button(button_frame, text="1. Scanner-Log öffnen", command=lambda: self._load_from_dialog(mode="scanner")).pack(side=tk.LEFT, padx=5); self.oms_button = ttk.Button(button_frame, text="2. OMS-Log hinzufügen", command=lambda: self._load_from_dialog(mode="oms"), state="disabled"); self.oms_button.pack(side=tk.LEFT, padx=5); self.search_button = ttk.Button(button_frame, text="Erweiterte Suche", command=self._open_advanced_search); self.search_button.pack(side=tk.LEFT, padx=5); filter_frame = ttk.Frame(main_frame, padding=(0, 5)); filter_frame.pack(fill=tk.X, pady=(10,0)); ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5)); ttk.Label(filter_frame, text="BagID:").pack(side=tk.LEFT, padx=(10, 5)); self.bag_id_filter = ttk.Combobox(filter_frame, width=15); self.bag_id_filter.pack(side=tk.LEFT); ttk.Label(filter_frame, text="IATA:").pack(side=tk.LEFT, padx=(10, 5)); self.iata_filter = ttk.Combobox(filter_frame, width=10); self.iata_filter.pack(side=tk.LEFT); self.iata_filter.bind("<<ComboboxSelected>>", self._apply_filters); ttk.Button(filter_frame, text="Anwenden", command=self._apply_filters).pack(side=tk.LEFT, padx=5); ttk.Button(filter_frame, text="Zurücksetzen", command=self._reset_filters).pack(side=tk.LEFT, padx=5); tree_frame = ttk.Frame(main_frame); tree_frame.pack(fill=tk.BOTH, expand=True, pady=(5,0)); self.tree = ttk.Treeview(tree_frame); scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set); scrollbar.pack(side=tk.RIGHT, fill=tk.Y); self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); self.tree.bind("<Double-1>", self._on_item_double_click); status_frame = ttk.Frame(main_frame); status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5); self.status_label = ttk.Label(status_frame, text="Bereit."); self.status_label.pack(side=tk.LEFT, padx=5)
    def _open_ftp_dialog(self):
        dialog = FTPDialogGateView(self); ftp_details = dialog.show()
        if ftp_details:
            local_dir = os.path.join(os.getcwd(), "logs", "gateview"); status_win = SFTPStatusWindow(self)
            def progress_callback(message, progress=None):
                self.after(0, status_win.update_status, message, progress)
            thread = threading.Thread(target=self._run_sftp_download, args=(ftp_details, local_dir, progress_callback, status_win), daemon=True); thread.start()
    def _run_sftp_download(self, details, local_dir, progress_callback, status_win):
        client = SFTPClient(details["host"], details["user"], details["passwd"])
        message, success = client.connect(progress_callback)
        if success:
            remote_files = [path for path in details["remote_paths"].values() if path]; total_files = len(remote_files); downloaded_so_far = 0
            def download_wrapper_callback(msg):
                nonlocal downloaded_so_far
                if "Lade herunter" in msg:
                    downloaded_so_far += 1; progress = int((downloaded_so_far / total_files) * 100); progress_callback(msg, progress)
                else:
                    progress_callback(msg)
            message, downloaded_files = client.download_files(remote_files, local_dir, download_wrapper_callback)
            if not downloaded_files:
                self.after(0, lambda: messagebox.showerror("SFTP Fehler", message, parent=self))
            else:
                self.after(0, self.on_ftp_download_complete, downloaded_files)
        else:
             self.after(0, lambda: messagebox.showerror("SFTP Fehler", message, parent=self))
        client.disconnect(); self.after(0, status_win.close_window)
    def on_ftp_download_complete(self, downloaded_files):
        messagebox.showinfo("Download Abgeschlossen", f"{len(downloaded_files)} Datei(en) heruntergeladen.\nAnalyse wird gestartet.", parent=self)
        self.raw_df = pd.DataFrame(); self._start_loading_process(downloaded_files)
    def _start_loading_process(self, file_paths):
        self._create_loading_window()
        thread = threading.Thread(target=self._load_and_process_files, args=(file_paths,), daemon=True); thread.start()
        self.after(100, self._check_thread, thread)
    def _load_from_dialog(self, mode):
        config = cfg.load_profiles()
        last_dir = config.get("last_gateview_dir", os.getcwd())
        file_path = filedialog.askopenfilename(title=f"{mode.upper()}-Log auswählen", initialdir=last_dir, filetypes=(("Logdateien", "*.log"), ("Alle Dateien", "*.*")))
        if not file_path: return
        config["last_gateview_dir"] = os.path.dirname(file_path); cfg.save_profiles(config)
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
    def _check_thread(self, thread):
        if thread.is_alive(): self.after(100, self._check_thread, thread)
        else: self.after(100, self._finalize_loading)
    def _load_and_process_files(self, file_paths):
        for file_path in file_paths:
            new_df = parse_log_file(file_path, lambda p, f: self.after(0, self._update_progress, p, f))
            self.raw_df = pd.concat([self.raw_df, new_df]).drop_duplicates().sort_values(by="Timestamp").reset_index(drop=True)
        self.journeys_df = consolidate_journeys(self.raw_df)
        self.after(0, lambda: self.oms_button.config(state="normal"))
    def _finalize_loading(self):
        if self.loading_win: self.loading_win.destroy(); self.loading_win = None
        self._update_gui_after_load()
    def _update_gui_after_load(self):
        self._populate_filters(); self._reset_filters()
        self.status_label.config(text=f"{len(self.journeys_df)} Gepäck-Durchläufe gefunden.")
        messagebox.showinfo("Erfolg", f"Analyse abgeschlossen. {len(self.journeys_df)} einzigartige Gepäck-Durchläufe gefunden.")
    def _populate_filters(self):
        if not self.journeys_df.empty: self.bag_id_filter['values'] = sorted(self.journeys_df['BagID'].unique()); self.iata_filter['values'] = sorted(self.journeys_df['IATA'].unique())
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
        self.tree["columns"] = list(df.columns); self.tree["show"] = "headings"
        for col in df.columns: self.tree.heading(col, text=col)
        self.tree.column("Operator", anchor='center')
        for index, row in df.iterrows(): self.tree.insert("", "end", values=list(row), iid=index)
    def _on_item_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        row_index = int(item_id); selected_journey = self.journeys_df.loc[row_index]; bag_id_to_find = selected_journey['BagID']
        self._show_bag_history_window(bag_id_to_find)
    def _show_iata_selection_window(self, journeys_df):
        win = tk.Toplevel(self); win.title("Mehrere Durchläufe gefunden"); win.geometry("500x300"); win.transient(self); win.grab_set(); ttk.Label(win, text="Diese IATA wurde mehrfach verwendet...").pack(pady=10, padx=10); cols = ["Timestamp", "BagID", "End-Status", "Operator"]; tree = ttk.Treeview(win, columns=cols, show="headings");
        for col in cols: tree.heading(col, text=col)
        for index, row in journeys_df.iterrows(): tree.insert("", "end", values=[row[c] for c in cols], iid=index)
        tree.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        def on_select(): item = tree.focus(); 
        if not item: messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie einen Eintrag.", parent=win); return
        self._update_treeview(self.journeys_df.loc[[int(item)]]); win.iconify()
        ttk.Button(win, text="Ausgewählten Durchlauf anzeigen", command=on_select).pack(pady=10)
    def _extract_routing_info(self, history_df):
        info = {'iata': 'N/A', 'machine_decision': 'N/A', 'operator_decision': 'N/A', 'final_command': 'N/A'}; 
        if history_df.empty: return info
        valid_iatas = history_df['IATA'][(history_df['IATA'] != 'N/A') & (history_df['IATA'] != 'NO_READ')]
        if not valid_iatas.empty: info['iata'] = valid_iatas.iloc[0]
        machine_dec_df = history_df[history_df['Klartext'].str.contains("Maschinelle Entscheidung")]
        if not machine_dec_df.empty:
            match = re.search(r":\s*(.+)", machine_dec_df.iloc[-1]['Klartext'])
            if match: info['machine_decision'] = match.group(1).replace("**", "")
        op_dec_df = history_df[history_df['Klartext'].str.contains("Finale Operator-Entscheidung|Späte Operator-Entscheidung")]
        if not op_dec_df.empty:
            match = re.search(r":\s*(.+)", op_dec_df.iloc[-1]['Klartext'])
            if match: info['operator_decision'] = match.group(1).replace("**", "")
        final_cmd_df = history_df[history_df['Klartext'].str.contains("Finaler Befehl an Förderanlage")]
        if not final_cmd_df.empty:
            match = re.search(r"gesendet: (.+)", final_cmd_df.iloc[-1]['Klartext'])
            if match: info['final_command'] = match.group(1).replace("**", "")
        return info
    def _show_bag_history_window(self, bag_id):
        win = tk.Toplevel(self); win.title(f"Detail-Analyse für BagID: {bag_id}"); win.geometry("1100x800")
        history_df = self.raw_df[self.raw_df['BagID'] == bag_id].sort_values(by="Timestamp")
        routing_info = self._extract_routing_info(history_df)
        summary_frame = ttk.LabelFrame(win, text="Analyse-Ergebnis (nur für diesen Durchlauf)", padding=10); summary_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(summary_frame, text="IATA:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky="w"); ttk.Label(summary_frame, text=routing_info['iata']).grid(row=0, column=1, sticky="w"); ttk.Label(summary_frame, text="Maschinen-Entscheid:", font=("Helvetica", 10, "bold")).grid(row=1, column=0, sticky="w"); ttk.Label(summary_frame, text=routing_info['machine_decision']).grid(row=1, column=1, sticky="w"); ttk.Label(summary_frame, text="Operator-Entscheid:", font=("Helvetica", 10, "bold")).grid(row=2, column=0, sticky="w"); ttk.Label(summary_frame, text=routing_info['operator_decision']).grid(row=2, column=1, sticky="w"); ttk.Label(summary_frame, text="Finaler Befehl an PLC:", font=("Helvetica", 10, "bold")).grid(row=3, column=0, sticky="w"); ttk.Label(summary_frame, text=routing_info['final_command']).grid(row=3, column=1, sticky="w");
        notebook = ttk.Notebook(win); notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        tab1 = ttk.Frame(notebook); notebook.add(tab1, text="Klartext-Analyse (BagID-bezogen)"); text1 = tk.Text(tab1, wrap=tk.WORD, font=("Courier New", 10)); text1.pack(fill=tk.BOTH, expand=True)
        tab2 = ttk.Frame(notebook); notebook.add(tab2, text="Scanner-Log Auszug (BagID-bezogen)"); text2 = tk.Text(tab2, wrap=tk.WORD, font=("Courier New", 9)); text2.pack(fill=tk.BOTH, expand=True)
        tab3 = ttk.Frame(notebook); notebook.add(tab3, text="OMS-Log Auszug (BagID-bezogen)"); text3 = tk.Text(tab3, wrap=tk.WORD, font=("Courier New", 9)); text3.pack(fill=tk.BOTH, expand=True)
        export_content = self._build_export_content(history_df, bag_id, routing_info)
        if not history_df.empty:
            history_df_no_duplicates = history_df[history_df['Klartext'] != history_df['Klartext'].shift()]
            header = f"Chronologische Analyse für BagID: {bag_id} (Wanne: {routing_info['iata']})\n"; text1.insert(tk.END, header + "=" * len(header) + "\n\n")
            for _, row in history_df_no_duplicates.iterrows(): full_line = f"[{row['Timestamp'].strftime('%H:%M:%S.%f')[:-3]}] {row['Klartext']}\n"; text1.insert(tk.END, full_line.replace("**", ""))
            scanner_logs_df = history_df[history_df['Source'] == 'Scanner']
            if not scanner_logs_df.empty:
                for _, row in scanner_logs_df.iterrows(): text2.insert(tk.END, row['OriginalLog'] + "\n")
            else: text2.insert(tk.END, f"Keine Scanner-Einträge für BagID {bag_id} gefunden.")
            oms_logs_df = history_df[history_df['Source'] == 'OMS']
            if not oms_logs_df.empty:
                for _, row in oms_logs_df.iterrows(): text3.insert(tk.END, f"[{row['Timestamp'].strftime('%H:%M:%S.%f')[:-3]}] {row['OriginalLog']}\n")
            else: text3.insert(tk.END, f"Keine OMS-Einträge für BagID {bag_id} gefunden.")
        else:
            msg = f"Keine Detail-Einträge für BagID {bag_id} gefunden."
            for txt in [text1, text2, text3]: txt.insert(tk.END, msg)
        for txt in [text1, text2, text3]: txt.config(state=tk.DISABLED)
        ttk.Button(win, text="Analyse speichern...", command=lambda: self._save_analysis(bag_id, routing_info['iata'], export_content)).pack(pady=10)
    def _build_export_content(self, history_df, bag_id, routing_info):
        if history_df.empty: return f"Keine Detail-Einträge für BagID {bag_id} gefunden."
        content_parts = [f"ANALYSE-REPORT FÜR BAGID {bag_id} (WANNE: {routing_info['iata']})", f"Erstellt am: {datetime.now().strftime('%d.%m.%Y um %H:%M:%S Uhr')}", "="*60, "\n--- ROUTING-ANALYSE ---", f"IATA: {routing_info['iata']}", f"Maschinen-Entscheid: {routing_info['machine_decision']}", f"Operator-Entscheid: {routing_info['operator_decision']}", f"Finaler Befehl an PLC: {routing_info['final_command']}\n", "--- KLARTEXT-ANALYSE (BAGID-BEZOGEN) ---"]
        history_df_no_duplicates = history_df[history_df['Klartext'] != history_df['Klartext'].shift()]
        for _, row in history_df_no_duplicates.iterrows(): content_parts.append(f"[{row['Timestamp'].strftime('%H:%M:%S.%f')[:-3]}] {row['Klartext'].replace('**', '')}")
        content_parts.append("\n--- SCANNER-LOG AUSZUG (BAGID-BEZOGEN) ---")
        scanner_logs = history_df[history_df['Source'] == 'Scanner']['OriginalLog']
        if not scanner_logs.empty: content_parts.extend(scanner_logs.tolist())
        else: content_parts.append("Keine Scanner-Logs für diesen Durchlauf gefunden.")
        content_parts.append("\n--- OMS-LOG AUSZUG (BAGID-BEZOGEN) ---")
        oms_logs_df = history_df[history_df['Source'] == 'OMS']
        if not oms_logs_df.empty:
            for _, row in oms_logs_df.iterrows(): content_parts.append(f"[{row['Timestamp'].strftime('%H:%M:%S.%f')[:-3]}] {row['OriginalLog']}")
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