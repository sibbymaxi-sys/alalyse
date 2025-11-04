# system_analyzer_app.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, font as tkfont
import pandas as pd
import threading
import os
import re
import sys
import traceback
import multiprocessing
from datetime import datetime, timedelta
import shutil

# Sicherer Import
try:
    from gateview_casefile_window import GateViewCasefileWindow
except ImportError:
    class GateViewCasefileWindow:
        def __init__(self, parent, selected_row, raw_df):
            messagebox.showerror("Fehler", "Detailfenster konnte nicht geladen werden (gateview_casefile_window.py fehlt).")
            win = tk.Toplevel(parent)
            win.title("Fehler")
            ttk.Label(win, text="Detailfenster konnte nicht geladen werden.").pack(padx=20, pady=20)

try:
    from clearscan_error_definitions import get_system_error_details
except ImportError:
    print("WARNUNG: clearscan_error_definitions.py nicht gefunden. Übersetzung ist deaktiviert.")
    # Fallback-Funktion, damit das Programm nicht abstürzt
    def get_system_error_details(filename, log_line):
        return None, None

class SystemAnalyzerApp:
    def __init__(self, parent):
        self.parent = parent
        self.parent.title("Eigenständige System-Analyse (ClearScan)")
        self.parent.geometry("1100x700")
        try:
            import sv_ttk
            sv_ttk.set_theme("dark")
        except Exception: pass
        style = ttk.Style(self.parent)
        style.map('Treeview', background=[('selected', '#343434')], foreground=[('selected', 'white')])
        try:
            default_font = tkfont.nametofont("TkDefaultFont")
            self.bold_font = default_font.copy()
            self.bold_font.configure(weight="bold")
            style.configure("Critical.Treeview", font=self.bold_font, foreground="red")
        except tk.TclError:
            print("Warnung: Konnte 'bold' Font für kritische Fehler nicht konfigurieren.")
            self.bold_font = None
        self.raw_df = pd.DataFrame()
        self.incidents_df = pd.DataFrame()
        self.loading_win = None
        self._setup_ui()

    def _setup_ui(self):
        main_frame = ttk.Frame(self.parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(control_frame, text="Log-Ordner analysieren", command=self._start_analysis_from_dialog).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Checkbox bleibt, steuert jetzt den relativen Filter
        self.filter_var = tk.BooleanVar(value=True) 
        ttk.Checkbutton(control_frame, text="Nur letzte 2 Tage (relativ) analysieren", variable=self.filter_var).pack(side=tk.LEFT, padx=15)
        
        ttk.Label(control_frame, text="Nach Datum filtern:").pack(side=tk.LEFT, padx=(5, 5))
        self.date_filter_combo = ttk.Combobox(control_frame, state="readonly", width=15)
        self.date_filter_combo.pack(side=tk.LEFT, padx=5)
        self.date_filter_combo.bind("<<ComboboxSelected>>", self._on_date_filter_select)
        
        ttk.Button(control_frame, text="Filter zurücksetzen (Alle anzeigen)", command=self._show_all_incidents).pack(side=tk.LEFT, padx=5)

        log_frame = ttk.LabelFrame(main_frame, text="Gefundene System-Ereignisse (Chronologisch)", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10,0))
        self.tree = ttk.Treeview(log_frame, columns=("Timestamp", "SourceFile", "Event"), show="headings")
        self.tree.heading("Timestamp", text="Zeitpunkt"); self.tree.column("Timestamp", width=150, anchor="w")
        self.tree.heading("SourceFile", text="Quelldatei", anchor="w"); self.tree.column("SourceFile", width=150, anchor="w")
        self.tree.heading("Event", text="Ereignis"); self.tree.column("Event", width=700, anchor="w")
        self.tree.bind("<Double-1>", self._on_item_select)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set); scrollbar.pack(side=tk.RIGHT, fill=tk.Y); self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.tag_configure("error", background="#4B2525")
        self.tree.tag_configure("critical", foreground="red")
        if self.bold_font: self.tree.tag_configure("critical", font=self.bold_font)
        self.tree.tag_configure("restart", foreground="#6495ED")
        status_bar = ttk.Frame(self.parent, padding=(5, 2)); status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = ttk.Label(status_bar, text="Bereit."); self.status_label.pack(side=tk.LEFT, padx=5)
    
    def _start_analysis_from_dialog(self):
        dir_path = filedialog.askdirectory(title="Wählen Sie den Log-Ordner zur System-Analyse")
        if not dir_path: return
        self._create_loading_window()
        
        filter_enabled = self.filter_var.get()
        # --- ÄNDERUNG: Name der Variable angepasst ---
        thread = threading.Thread(target=self._run_analysis_thread, args=(dir_path, filter_enabled), daemon=True) 
        thread.start()

    def _run_analysis_thread(self, dir_path, filter_relatively=False):
        def progress_callback(progress, message): self.parent.after(0, self._update_progress, progress, message)
        
        files_to_exclude = ['yum.log', 'oms.log', 'scanner_bag.log', 'app.log']
        log_files_to_analyze = []
        progress_callback(0, "Durchsuche Verzeichnis nach Log-Dateien...")
        
        # --- LOGIK ENTFERNT ---
        # Die Datums-Limits (file_date_limit, line_date_limit) werden
        # hier entfernt, da wir sie erst *nach* dem Lesen kennen.
        
        for root, _, files in os.walk(dir_path):
            for file in files:
                filename = os.path.basename(file)
                filename_lower = filename.lower()
                
                if filename_lower in files_to_exclude or filename_lower.startswith('alg'):
                    continue
                
                has_extension = '.' in filename
                is_log_file = filename_lower.endswith('.log') or filename_lower.endswith('.csv')
                is_known_no_ext = not has_extension and any(filename_lower.startswith(p) for p in ['dcs_', 'diagserv_', 'scs_', 'syserror_', 'current'])

                if is_log_file or is_known_no_ext:
                    file_path = os.path.join(root, file)
                    
                    # --- LOGIK ENTFERNT ---
                    # Der Filter, der ganze *Dateien* übersprungen hat,
                    # wurde entfernt. Wir müssen alle Dateien lesen.
                    
                    log_files_to_analyze.append(file_path)
        
        if not log_files_to_analyze:
            self.parent.after(0, self._finalize_analysis, False, "Keine relevanten Log-Dateien gefunden.")
            return
            
        analysis_files = log_files_to_analyze
        all_entries = []
        for i, file_path in enumerate(analysis_files):
            filename = os.path.basename(file_path)
            progress_callback(int(((i + 1) / len(analysis_files)) * 100), f"Lese: {filename}")
            
            try:
                current_year_for_file = str(datetime.now().year)
                
                for enc in ['utf-8', 'latin1', 'cp1252']:
                    try:
                        with open(file_path, 'r', encoding=enc) as f:
                            for line_num, line in enumerate(f): 
                                line = line.strip()
                                if not line: continue
                                
                                timestamp, message_start_pos = self._parse_timestamp(line, current_year_for_file)
                                if timestamp is None: continue
                                
                                # --- LOGIK ENTFERNT ---
                                # Der 'break'-Befehl (das Stoppen des Lesens
                                # alter Zeilen) wurde entfernt. Wir lesen
                                # jetzt alle Zeilen aus allen Dateien.
                                
                                category, clean_message = self._categorize_and_clean_message(line, filename) 
                                if not category: continue
                                    
                                final_message = f"[{category}] {clean_message}"
                                all_entries.append({'Timestamp': timestamp, 'SourceFile': filename, 'Event': final_message, 'OriginalLog': line})
                        
                        break
                    
                    except UnicodeDecodeError: 
                        continue 
                    except Exception as e: 
                        print(f"Fehler bei Kodierung {enc} für {filename}: {e}")
                        break 
            
            except Exception as e: 
                print(f"FEHLER beim Verarbeiten der Datei {filename}: {e}")
                
        if not all_entries:
            self.parent.after(0, self._finalize_analysis, False, "Keine relevanten Ereignisse in den Log-Dateien gefunden.")
            return
            
        self.raw_df = pd.DataFrame(all_entries)
        self.raw_df['Timestamp'] = pd.to_datetime(self.raw_df['Timestamp'], errors='coerce')
        original_count = len(self.raw_df)
        self.raw_df.dropna(subset=['Timestamp'], inplace=True)
        dropped_count = original_count - len(self.raw_df)
        if dropped_count > 0: print(f"WARNUNG: {dropped_count} Zeilen wurden wegen ungültiger Zeitstempel entfernt.")
        
        if self.raw_df.empty:
            self.parent.after(0, self._finalize_analysis, False, "Keine gültigen Zeitstempel in den Ereignissen gefunden.")
            return

        self.raw_df.sort_values(by="Timestamp", na_position='first', inplace=True)
        self.raw_df.reset_index(drop=True, inplace=True)
        
        # --- NEUE RELATIVE FILTER-LOGIK ---
        msg_suffix = "."
        if filter_relatively:
            # Finde den absolut neuesten Zeitstempel in allen gelesenen Daten
            max_ts = self.raw_df['Timestamp'].max()
            if pd.notna(max_ts):
                # Berechne das Startdatum (max_ts - 2 Tage)
                line_date_limit = max_ts - timedelta(days=2)
                # Wende den Filter auf den DataFrame an
                self.incidents_df = self.raw_df[self.raw_df['Timestamp'] >= line_date_limit].copy()
                msg_suffix = f" (gefiltert auf 2 Tage vor dem {max_ts.strftime('%Y-%m-%d %H:%M')})."
            else:
                self.incidents_df = self.raw_df.copy() # Fallback, falls keine Daten gefunden
        else:
            # Filter ist aus, nimm alle Daten
            self.incidents_df = self.raw_df.copy() 
        
        self.parent.after(0, self._finalize_analysis, True, f"{len(self.incidents_df)} relevante Ereignisse gefunden{msg_suffix}")

    def _categorize_and_clean_message(self, original_line, filename):
        line_lower = original_line.lower()
        
        category, message = get_system_error_details(filename, original_line)
        if category:
            return category, message 

        if any(kw in line_lower for kw in ['fatal', 'critical', 'exception', 'traceback', 'segmentation fault', 'core dumped', 'panic', 'assert']): category = "Fatal"
        elif any(kw in line_lower for kw in ['failed to initialize', 'startup failed', 'cannot start', 'unable to load']): category = "Startup"
        elif any(kw in line_lower for kw in ['cannot connect', 'connection refused', 'timeout', 'database error', "statement returned multiple rows"]): category = "Connection"
        elif any(kw in line_lower for kw in ['license invalid', 'license expired', 'no valid license']): category = "License"
        elif any(kw in line_lower for kw in ['config error', 'invalid configuration', 'missing file']): category = "Config"
        elif any(kw in line_lower for kw in ['device error', 'driver error', 'hardware fault']): category = "Hardware"
        elif any(kw in line_lower for kw in ['error', 'fail', 'fault']): category = "Error"
        elif 'warning' in line_lower or '[ warning ]' in line_lower: category = "Warning"
        elif 'restarting script' in line_lower: category = "Restart"
        else: return None, original_line

        message = original_line
        _, msg_start = self._parse_timestamp(message, str(datetime.now().year))
        if msg_start is not None: message = message[msg_start:].strip()
        
        message = re.sub(r'^\[.*?\]\s*:\s*', '', message) 
        message = re.sub(r'^\(null\)\s*\[\s*(warning|debug)\s*\]\s*\d{2}:\d{2}:\d{2}\.\d{3}:\s*', '', message, flags=re.IGNORECASE)
        message = re.sub(r'^(?:ERROR|WARNING|INFO|DEBUG|FATAL|CRITICAL)\s*[:\-]\s*', '', message, flags=re.IGNORECASE)
        message = message.replace('!!!! Warning: Station', 'Station')
        message = message.replace('!!!! Warning:  - Fault: ', 'Fault: ')
        message = re.sub(r'in\s+[\/\w\.\-]+\s*:\s*', '', message) 
        message = re.sub(r'0x[0-9a-fA-F]+\b', '', message)
        message = re.sub(r': None$', '', message) 
        
        return category, message.strip()

    def _parse_timestamp(self, line, year):
        line_cleaned = re.sub(r'^[a-zA-Z\._]+:\s*', '', line)

        patterns = [
            (r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\.\d{2}\.\d{3})', '%Y-%m-%d %H:%M.%S.%f'), 
            (r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,\.]\d{3})', '%Y-%m-%d %H:%M:%S.%f'),
            (r'^(\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4})', '%a %b %d %H:%M:%S %Y'),
            (r'^(\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\.\d{3})', f'%a %b %d %H:%M:%S.%f {year}'),
            (r'^(\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})', f'%a %b %d %H:%M:%S {year}'),
            (r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)', 'iso'),
            (r'^(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', f'{year}-%m-%d %H:%M:%S')
        ]
        
        for pattern, fmt in patterns:
            match = re.match(pattern, line_cleaned)
            if match:
                ts_str = match.group(1)
                end_pos = line.find(ts_str) + len(ts_str) 
                try:
                    if fmt == 'iso': dt = pd.to_datetime(ts_str).tz_localize(None)
                    else:
                         ts_str_clean = ts_str.replace(',', '.')
                         if fmt == f'%a %b %d %H:%M:%S {year}':
                             dt = pd.to_datetime(ts_str_clean, format='%a %b %d %H:%M:%S %Y')
                         elif fmt == f'%a %b %d %H:%M:%S.%f {year}':
                              dt = pd.to_datetime(ts_str_clean, format='%a %b %d %H:%M:%S.%f %Y')
                         else:
                             dt = pd.to_datetime(ts_str_clean, format=fmt) 
                    if pd.notna(dt): return dt, end_pos
                except ValueError:
                    try: 
                        dt = pd.to_datetime(ts_str.replace(',', '.'))
                        if pd.notna(dt): return dt, end_pos
                    except ValueError:
                        continue 
        return None, None

    def _finalize_analysis(self, success, message):
        if self.loading_win: self.loading_win.destroy(); self.loading_win = None
        if not success:
            messagebox.showwarning("Analyse fehlgeschlagen", message, parent=self.parent)
            self.raw_df = pd.DataFrame()
            self.incidents_df = pd.DataFrame()
            self._update_treeview(pd.DataFrame()) 
            self._populate_date_filter()
            return
            
        self._show_all_incidents() 
        self.status_label.config(text=message)
        self._populate_date_filter() 
        
        messagebox.showinfo("System-Analyse abgeschlossen", message, parent=self.parent)

    def _populate_date_filter(self): 
        df_for_filter = self.incidents_df
        self.date_filter_combo.set('')
        if df_for_filter.empty or 'Timestamp' not in df_for_filter.columns or df_for_filter['Timestamp'].isnull().all():
            self.date_filter_combo['values'] = []
            return
        valid_dates = df_for_filter['Timestamp'].dropna()
        if not valid_dates.empty:
            try:
                unique_dates = sorted(valid_dates.dt.date.unique())
                self.date_filter_combo['values'] = [d.strftime('%Y-%m-%d') for d in unique_dates]
            except AttributeError: self.date_filter_combo['values'] = []
    
    def _on_date_filter_select(self, event=None):
        selected_date_str = self.date_filter_combo.get()
        if not selected_date_str: return
        try:
            selected_date = pd.to_datetime(selected_date_str).date()
            mask = self.incidents_df['Timestamp'].dt.date == selected_date
            filtered_df = self.incidents_df.loc[mask]
            self._update_treeview(filtered_df)
            self.status_label.config(text=f"{len(filtered_df)} Ereignisse am {selected_date_str} gefunden.")
        except (ValueError, AttributeError): pass

    def _show_all_incidents(self):
        if self.incidents_df.empty: 
            self._update_treeview(self.incidents_df) 
            self.status_label.config(text="Keine Ereignisse zum Anzeigen.")
            return
        self.date_filter_combo.set('')
        self._update_treeview(self.incidents_df)
        self.status_label.config(text=f"Zeige alle {len(self.incidents_df)} gefundenen Ereignisse.")

    def _show_last_two_days(self):
        # Diese Funktion wird nicht mehr direkt von einem Button aufgerufen,
        # aber wir lassen sie für den Fall, dass sie intern nützlich ist.
        # Die Logik ist jetzt der relative Filter im _run_analysis_thread.
        if self.incidents_df.empty:
             self._update_treeview(self.incidents_df)
             self.status_label.config(text="Keine Ereignisse zum Anzeigen.")
             return
        now = pd.Timestamp.now()
        two_days_ago = now - pd.Timedelta(days=2)
        mask = self.incidents_df['Timestamp'] >= two_days_ago
        filtered_df = self.incidents_df.loc[mask]
        self._update_treeview(filtered_df)
        self.date_filter_combo.set('')
        self.status_label.config(text=f"Zeige Ereignisse der letzten 48 Stunden ({len(filtered_df)} Einträge).")
        
    def _update_treeview(self, df):
        for i in self.tree.get_children(): self.tree.delete(i)
        
        # --- FIX: Verhindert Absturz, wenn df None ist ---
        if df is None: 
            df = pd.DataFrame() 
        
        # --- FIX: Verhindert Absturz, wenn df leer ist ---
        if df.empty:
            return

        for index in df.index: 
            if index not in df.index: continue 
            row = df.loc[index]
            tags = []
            event_text = row['Event']
            if event_text.startswith("[Fatal]"): tags.append("critical")
            elif event_text.startswith("[Restart]"): tags.append("restart")
            elif event_text.startswith(("[Startup]", "[Connection]", "[License]", "[Config]", "[Hardware]", "[Error]", "[Warning]")): 
                tags.append("error")
            self.tree.insert("", "end", iid=index, tags=tuple(tags), values=(
                row['Timestamp'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['Timestamp']) else 'N/A', 
                row['SourceFile'], 
                event_text 
            ))
            
    def _on_item_select(self, event):
        selected_item = self.tree.focus()
        if not selected_item: return
        try:
            row_index = int(selected_item) 
            selected_raw_row = self.raw_df.loc[row_index] 
            GateViewCasefileWindow(self.parent, selected_raw_row, self.raw_df)
        except (ValueError, KeyError, AttributeError) as e:
             print(f"Fehler beim Öffnen des Detailfensters: {e}")
             messagebox.showwarning("Fehler", "Detailansicht konnte nicht geöffnet werden.", parent=self.parent)

    def _create_loading_window(self):
        self.loading_win = tk.Toplevel(self.parent); self.loading_win.title("Ladevorgang"); self.loading_win.geometry("450x130"); self.loading_win.resizable(False, False); self.parent.update_idletasks(); x = self.parent.winfo_screenwidth() // 2 - self.loading_win.winfo_width() // 2; y = self.parent.winfo_screenheight() // 2 - self.loading_win.winfo_height() // 2; self.loading_win.geometry(f"+{x}+{y}"); self.loading_win.transient(self.parent); self.loading_win.grab_set(); self.loading_label = ttk.Label(self.loading_win, text="Initialisiere...", font=("Helvetica", 10)); self.loading_label.pack(pady=(15, 5), padx=10, anchor="w"); self.loading_progress_bar = ttk.Progressbar(self.loading_win, orient="horizontal", mode="determinate"); self.loading_progress_bar.pack(fill=tk.X, expand=True, padx=10); self.percent_label = ttk.Label(self.loading_win, text="0%", font=("Helvetica", 10)); self.percent_label.pack(pady=5)
    
    def _update_progress(self, progress, filename):
        if self.loading_win: self.loading_win.lift(); self.loading_label.config(text=f"Verarbeite: {filename}"); self.loading_progress_bar['value'] = progress; self.percent_label.config(text=f"{progress}%"); self.loading_win.update_idletasks()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    root = tk.Tk()
    app = SystemAnalyzerApp(root)
    root.mainloop()