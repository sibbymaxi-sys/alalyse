#!/usr/bin/env python3
# gateview_app.py
# GateView v7.3 (Multi-Page PDF Fix) – © 2025 Patrick Oppermann

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import threading
import os
import re
from datetime import datetime
import sv_ttk
from tkcalendar import DateEntry

# KORREKTUR: Alle notwendigen ReportLab-Module importiert
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Spacer, Frame, PageTemplate, BaseDocTemplate
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from log_parser import parse_log_file
from data_processor import consolidate_journeys, calculate_kpis
from advanced_search_dialog import AdvancedSearchDialog
from base_app import BaseApp

class GateViewApp(BaseApp):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, app_name="GateView Analyzer", version="7.3", *args, **kwargs)
        
        self.raw_df = pd.DataFrame()
        self.journeys_df = pd.DataFrame()
        self.kpis = {}
        self.loading_win = None
        
        self._setup_ui()

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding="10"); main_frame.pack(fill=tk.BOTH, expand=True)
        button_frame = ttk.Frame(main_frame); button_frame.pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="1. Scanner-Log öffnen", command=lambda: self._load_files_threaded(mode="scanner")).pack(side=tk.LEFT, padx=5)
        self.oms_button = ttk.Button(button_frame, text="2. OMS-Log hinzufügen", command=lambda: self._load_files_threaded(mode="oms"), state="disabled"); self.oms_button.pack(side=tk.LEFT, padx=5)
        self.search_button = ttk.Button(button_frame, text="Erweiterte Suche", command=self._open_advanced_search); self.search_button.pack(side=tk.LEFT, padx=5)
        self.stats_button = ttk.Button(button_frame, text="Statistik-Dashboard", command=self._show_stats_dashboard, state="disabled"); self.stats_button.pack(side=tk.LEFT, padx=5)
        filter_frame = ttk.Frame(main_frame, padding=(0, 5)); filter_frame.pack(fill=tk.X)
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5)); ttk.Label(filter_frame, text="BagID:").pack(side=tk.LEFT, padx=(10, 5))
        self.bag_id_filter = ttk.Combobox(filter_frame, width=15); self.bag_id_filter.pack(side=tk.LEFT)
        ttk.Label(filter_frame, text="IATA:").pack(side=tk.LEFT, padx=(10, 5))
        self.iata_filter = ttk.Combobox(filter_frame, width=10); self.iata_filter.pack(side=tk.LEFT)
        self.iata_filter.bind("<<ComboboxSelected>>", self._apply_filters)
        ttk.Button(filter_frame, text="Anwenden", command=self._apply_filters).pack(side=tk.LEFT, padx=5); ttk.Button(filter_frame, text="Zurücksetzen", command=self._reset_filters).pack(side=tk.LEFT, padx=5)
        tree_frame = ttk.Frame(main_frame); tree_frame.pack(fill=tk.BOTH, expand=True, pady=(5,0))
        self.tree = ttk.Treeview(tree_frame)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y); self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self._on_item_double_click)
        status_frame = ttk.Frame(main_frame); status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        self.status_label = ttk.Label(status_frame, text="Bereit."); self.status_label.pack(side=tk.LEFT, padx=5)

    def _create_loading_window(self):
        self.loading_win = tk.Toplevel(self); self.loading_win.title("Ladevorgang"); self.loading_win.geometry("450x130"); self.loading_win.resizable(False, False)
        self.update_idletasks(); x = self.winfo_screenwidth() // 2 - self.loading_win.winfo_width() // 2; y = self.winfo_screenheight() // 2 - self.loading_win.winfo_height() // 2; self.loading_win.geometry(f"+{x}+{y}")
        self.loading_win.transient(self); self.loading_win.grab_set()
        self.loading_label = ttk.Label(self.loading_win, text="Initialisiere...", font=("Helvetica", 10)); self.loading_label.pack(pady=(15, 5), padx=10, anchor="w")
        self.loading_progress_bar = ttk.Progressbar(self.loading_win, orient="horizontal", mode="determinate"); self.loading_progress_bar.pack(fill=tk.X, expand=True, padx=10)
        self.percent_label = ttk.Label(self.loading_win, text="0%", font=("Helvetica", 10)); self.percent_label.pack(pady=5)

    def _update_progress(self, progress, filename):
        if self.loading_win:
            self.loading_win.lift(); self.loading_label.config(text=f"Verarbeite: {filename}")
            self.loading_progress_bar['value'] = progress; self.percent_label.config(text=f"{progress}%")
            self.loading_win.update_idletasks()

    def _load_files_threaded(self, mode):
        if mode == "scanner": file_path = filedialog.askopenfilename(title="Scanner-Log auswählen", filetypes=(("Logdateien", "*.log"), ("Alle Dateien", "*.*"))); self.raw_df = pd.DataFrame()
        elif mode == "oms": file_path = filedialog.askopenfilename(title="OMS-Log auswählen", filetypes=(("Logdateien", "*.log"), ("Alle Dateien", "*.*")))
        if not file_path: return
        self._create_loading_window()
        thread = threading.Thread(target=self._load_and_process_files, args=([file_path], mode), daemon=True)
        thread.start()
        self.after(100, self._check_thread, thread)

    def _check_thread(self, thread):
        if thread.is_alive(): self.after(100, self._check_thread, thread)
        else: self.after(100, self._finalize_loading)

    def _load_and_process_files(self, file_paths, mode):
        for file_path in file_paths:
            new_df = parse_log_file(file_path, lambda p, f: self.after(0, self._update_progress, p, f))
            self.raw_df = pd.concat([self.raw_df, new_df]).drop_duplicates().sort_values(by="Timestamp").reset_index(drop=True)
        self.journeys_df = consolidate_journeys(self.raw_df)
        if mode == "scanner": self.after(0, lambda: self.oms_button.config(state="normal"))
        self.after(0, lambda: self.stats_button.config(state="normal"))

    def _finalize_loading(self):
        if self.loading_win: self.loading_win.destroy(); self.loading_win = None
        self._update_gui_after_load()

    def _update_gui_after_load(self):
        self._populate_filters(); self._reset_filters()
        self.status_label.config(text=f"{len(self.journeys_df)} Gepäck-Durchläufe gefunden.")
        messagebox.showinfo("Erfolg", f"Analyse abgeschlossen. {len(self.journeys_df)} einzigartige Gepäck-Durchläufe gefunden.")

    def _open_advanced_search(self):
        dialog = AdvancedSearchDialog(self); criteria = dialog.show()
        if criteria: self._perform_advanced_search(criteria)

    def _perform_advanced_search(self, criteria):
        df = self.journeys_df.copy()
        if criteria['bag_id']: df = df[df['BagID'].str.contains(criteria['bag_id'], case=False, na=False)]
        if criteria['iata']: df = df[df['IATA'].str.contains(criteria['iata'], case=False, na=False)]
        try:
            if criteria['start_date']:
                start_date = pd.to_datetime(criteria['start_date']).normalize()
                df = df[df['Timestamp'] >= start_date]
            if criteria['end_date']:
                end_date = pd.to_datetime(criteria['end_date']).normalize() + pd.Timedelta(days=1)
                df = df[df['Timestamp'] < end_date]
        except Exception as e: messagebox.showerror("Ungültiges Datum", f"Format: YYYY-MM-DD.\nFehler: {e}"); return
        if criteria['oms_only']:
            oms_bag_ids = self.raw_df[self.raw_df['Source'] == 'OMS']['BagID'].unique()
            df = df[df['BagID'].isin(oms_bag_ids)]
        self._update_treeview(df)
        self.status_label.config(text=f"{len(df)} Einträge nach erweiterter Suche gefunden.")

    def _populate_filters(self):
        if not self.journeys_df.empty:
            self.bag_id_filter['values'] = sorted(self.journeys_df['BagID'].unique())
            self.iata_filter['values'] = sorted(self.journeys_df['IATA'].unique())
    
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
        for index, row in df.iterrows(): self.tree.insert("", "end", values=list(row), iid=index)

    def _on_item_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        row_index = int(item_id); selected_journey = self.journeys_df.loc[row_index]; bag_id_to_find = selected_journey['BagID']
        self._show_bag_history_window(bag_id_to_find)

    def _show_iata_selection_window(self, journeys_df):
        win = tk.Toplevel(self); win.title("Mehrere Durchläufe gefunden"); win.geometry("500x300"); win.transient(self); win.grab_set()
        ttk.Label(win, text="Diese IATA wurde mehrfach verwendet...").pack(pady=10, padx=10)
        cols = ["Timestamp", "BagID", "End-Status"]; tree = ttk.Treeview(win, columns=cols, show="headings")
        for col in cols: tree.heading(col, text=col)
        for index, row in journeys_df.iterrows(): tree.insert("", "end", values=[row[c] for c in cols], iid=index)
        tree.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        def on_select():
            item = tree.focus()
            if not item: messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie einen Eintrag.", parent=win); return
            self._update_treeview(self.journeys_df.loc[[int(item)]]); win.destroy()
        ttk.Button(win, text="Ausgewählten Durchlauf anzeigen", command=on_select).pack(pady=10)
    
    def _show_bag_history_window(self, bag_id):
        win = tk.Toplevel(self); win.title(f"Detail-Analyse für BagID: {bag_id}"); win.geometry("1000x700")
        notebook = ttk.Notebook(win); notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        def create_scrollable_text_tab(parent, title):
            tab = ttk.Frame(parent); scrollbar = ttk.Scrollbar(tab); scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            text_widget = tk.Text(tab, wrap=tk.WORD, yscrollcommand=scrollbar.set, font=("Courier New", 10), state="disabled")
            text_widget.pack(fill=tk.BOTH, expand=True); scrollbar.config(command=text_widget.yview)
            parent.add(tab, text=title); return text_widget

        text1 = create_scrollable_text_tab(notebook, "Klartext-Analyse")
        text2 = create_scrollable_text_tab(notebook, "Scanner-Log Auszug")
        text3 = create_scrollable_text_tab(notebook, "OMS-Log Auszug")
        text4 = create_scrollable_text_tab(notebook, "Zusammenfassung")
        
        text1.tag_configure("bold", font=("Courier New", 10, "bold"))
        
        history_df = self.raw_df[self.raw_df['BagID'] == bag_id].sort_values(by="Timestamp")
        
        if not history_df.empty:
            history_df_unique = history_df[history_df['Klartext'] != history_df['Klartext'].shift()]
            valid_iatas = history_df_unique['IATA'][(history_df_unique['IATA'] != 'N/A') & (history_df_unique['IATA'] != 'NO_READ')]
            iata = valid_iatas.iloc[0] if not valid_iatas.empty else 'NO_READ'
            
            header = f"Chronologische Analyse für BagID: {bag_id} (Wanne: {iata})\n"
            
            for txt in [text1, text2, text3, text4]: txt.config(state=tk.NORMAL)
            
            text1.insert(tk.END, header + "=" * len(header) + "\n\n")

            for _, row in history_df_unique.iterrows():
                full_line = f"[{row['Timestamp'].strftime('%H:%M:%S.%f')[:-3]}] {row['Klartext']}\n"; start_index = text1.index(tk.END); text1.insert(tk.END, full_line)
                for match in re.finditer(r"\*\*([^*]+)\*\*", row['Klartext']):
                    keyword = match.group(1); kw_start_pos = text1.search(keyword, start_index, tk.END)
                    if kw_start_pos:
                        kw_end_pos = f"{kw_start_pos}+{len(keyword)}c"; text1.tag_add("bold", kw_start_pos, kw_end_pos)
                clean_line = full_line.replace("**", ""); text1.delete(start_index, tk.END); text1.insert(start_index, clean_line)

            for _, row in history_df.iterrows():
                 if row['Source'] == 'Scanner': text2.insert(tk.END, row['OriginalLog'] + "\n")
                 elif row['Source'] == 'OMS': text3.insert(tk.END, f"{row['Klartext']}\n{row['OriginalLog']}\n\n")
            
            summary_content = ("--- KLARTEXT-ANALYSE ---\n\n" + text1.get("1.0", tk.END) +
                               "\n\n--- SCANNER-LOG AUSZUG ---\n\n" + text2.get("1.0", tk.END) +
                               "\n\n--- OMS-LOG AUSZUG ---\n\n" + text3.get("1.0", tk.END))
            text4.insert(tk.END, summary_content)
        else:
            msg = f"Keine Detail-Einträge für BagID {bag_id} gefunden."
            for txt in [text1, text2, text3, text4]: txt.config(state=tk.NORMAL); txt.insert(tk.END, msg)

        for txt in [text1, text2, text3, text4]: txt.config(state=tk.DISABLED)
        ttk.Button(win, text="Analyse als PDF speichern", command=lambda: self._export_analysis_to_pdf(history_df, bag_id)).pack(pady=10)

    def _export_analysis_to_pdf(self, history_df, bag_id):
        save_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF-Dateien", "*.pdf")], initialfile=f"Analyse_{bag_id}.pdf", parent=self)
        if not save_path: return
        
        if history_df.empty:
            messagebox.showwarning("Keine Daten", "Es gibt keine Daten zum Speichern.", parent=self)
            return
            
        try:
            valid_iatas = history_df['IATA'][(history_df['IATA'] != 'N/A') & (history_df['IATA'] != 'NO_READ')]
            iata = valid_iatas.iloc[0] if not valid_iatas.empty else 'NO_READ'
            
            doc = BaseDocTemplate(save_path, pagesize=A4)
            styles = getSampleStyleSheet(); styles['Code'].wordWrap = 'CJK'
            
            def highlight(text):
                text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                return re.sub(r'(ALARM|NO_READ|override|überschrieben|SICHERHEITSREGEL|\*\*.*?\*\*)', r'<b>\1</b>', text, flags=re.IGNORECASE).replace("**", "")

            story = []
            story.append(Paragraph(f"<b>Analyse-Report für BagID {bag_id} (Wanne: {iata})</b>", styles['h1']))
            story.append(Paragraph(f"Erstellt am {datetime.now().strftime('%d.%m.%Y um %H:%M:%S Uhr')}", styles['Normal'])); story.append(Spacer(1, 0.5*cm))
            
            history_df_unique = history_df[history_df['Klartext'] != history_df['Klartext'].shift()]
            
            story.append(Paragraph("<b><u>Klartext-Analyse (Zusammenfassung)</u></b>", styles['h2']))
            for _, row in history_df_unique.iterrows():
                line = f"[{row['Timestamp'].strftime('%H:%M:%S.%f')[:-3]}] {row['Klartext']}"
                story.append(Paragraph(highlight(line), styles['Code']))
            
            story.append(Spacer(1, 0.5*cm)); story.append(Paragraph("<b><u>Scanner-Log Auszug (Rohdaten)</u></b>", styles['h2']))
            for log in history_df[history_df['Source'] == 'Scanner']['OriginalLog']:
                story.append(Paragraph(log.replace("\n", "<br/>"), styles['Code']))

            story.append(Spacer(1, 0.5*cm)); story.append(Paragraph("<b><u>OMS-Log Auszug (Rohdaten)</u></b>", styles['h2']))
            for log in history_df[history_df['Source'] == 'OMS']['OriginalLog']:
                story.append(Paragraph(log.replace("\n", "<br/>"), styles['Code']))
            
            doc.build(story)
            
            messagebox.showinfo("Erfolg", f"PDF erfolgreich gespeichert unter:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Fehler", f"PDF konnte nicht erstellt werden:\n{e}", parent=self)
        
    def _show_stats_dashboard(self):
        # ... (Diese Funktion bleibt unverändert) ...
        pass