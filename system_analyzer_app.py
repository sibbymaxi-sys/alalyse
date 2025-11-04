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
from datetime import datetime, timedelta, date # Import date
import shutil

# ... (Imports und Helper-Funktionen _parse_timestamp_static, _categorize_and_clean_message_static, _process_log_file bleiben unverändert) ...
try:
    from cs_error_definitions import get_system_error_details
except ImportError:
    print("WARNUNG: cs_error_definitions.py nicht gefunden.")
    def get_system_error_details(filename, log_line): return None, None # Fallback

try:
    from gateview_casefile_window import GateViewCasefileWindow
except ImportError:
    class GateViewCasefileWindow: # Fallback
        def __init__(self, parent, selected_row, raw_df):
            messagebox.showerror("Fehler", "Detailfenster konnte nicht geladen werden.")
            win = tk.Toplevel(parent); win.title("Fehler")
            ttk.Label(win, text="Detailfenster nicht geladen.").pack(padx=20, pady=20)

def _parse_timestamp_static(line, year_str):
    # (Code unverändert)
    line_cleaned = re.sub(r'^[a-zA-Z\._]+:\s*', '', line); year = int(year_str) if year_str.isdigit() else datetime.now().year
    patterns = [ (r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\.\d{2}\.\d{3})', '%Y-%m-%d %H:%M.%S.%f', False), (r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,\.]\d{3})', '%Y-%m-%d %H:%M:%S.%f', False), (r'^(\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\.\d{3}\s+\d{4})', '%a %b %d %H:%M:%S.%f %Y', False), (r'^(\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4})', '%a %b %d %H:%M:%S %Y', False), (r'^(\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\.\d{3})', '%a %b %d %H:%M:%S.%f', True), (r'^(\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})', '%a %b %d %H:%M:%S', True), (r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)', 'iso', False), (r'^(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', '%m-%d %H:%M:%S', True) ]
    for pattern, fmt, needs_year in patterns:
        match = re.match(pattern, line_cleaned)
        if match:
            ts_str = match.group(1); end_pos_match = re.match(pattern, line)
            if end_pos_match: end_pos = end_pos_match.end(1)
            else: end_pos_fallback = line.find(ts_str); end_pos = end_pos_fallback + len(ts_str) if end_pos_fallback != -1 else None; continue
            try:
                dt = None; ts_str_clean = ts_str.replace(',', '.')
                if fmt == 'iso': dt = pd.to_datetime(ts_str_clean).tz_localize(None)
                elif needs_year:
                    try: dt = pd.to_datetime(f"{ts_str_clean} {year}", format=f"{fmt} %Y")
                    except ValueError:
                         try: dt = pd.to_datetime(f"{ts_str_clean} {year-1}", format=f"{fmt} %Y")
                         except ValueError: continue
                else: dt = pd.to_datetime(ts_str_clean, format=fmt)
                if pd.notna(dt): return dt, end_pos
            except ValueError: continue
    try:
        dt_fallback = pd.to_datetime(line, errors='coerce', infer_datetime_format=True)
        if pd.notna(dt_fallback):
             if dt_fallback.year < 1970:
                 try: dt_fallback = dt_fallback.replace(year=year)
                 except ValueError: pass
             return dt_fallback, None
    except Exception: pass
    return None, None

def _categorize_and_clean_message_static(original_line, filename, year_str):
    # (Code unverändert)
    category, message = get_system_error_details(filename, original_line);
    if category: return category, message
    line_lower = original_line.lower()
    cat_map = { 'Fatal': ['fatal', 'critical', 'exception', 'traceback', 'segmentation fault', 'core dumped', 'panic', 'assert'], 'Restart': ['restarting script'], 'Startup': ['failed to initialize', 'startup failed', 'cannot start', 'unable to load'], 'Connection': ['cannot connect', 'connection refused', 'timeout', 'database error', "statement returned multiple rows"], 'License': ['license invalid', 'license expired', 'no valid license'], 'Config': ['config error', 'invalid configuration', 'missing file'], 'Hardware': ['device error', 'driver error', 'hardware fault'], 'Error': ['error', 'fail', 'fault'], 'Warning': ['warning', '[ warning ]'] }
    category = next((cat for cat, keywords in cat_map.items() if any(kw in line_lower for kw in keywords)), None)
    if not category: return None, None
    message = original_line; _, msg_start = _parse_timestamp_static(message, year_str)
    if msg_start is not None and msg_start < len(message): message = message[msg_start:].strip()
    message = re.sub(r'^\[.*?\]\s*:\s*', '', message); message = re.sub(r'^\(null\)\s*\[\s*(warning|debug)\s*\]\s*\d{2}:\d{2}:\d{2}\.\d{3}:\s*', '', message, flags=re.IGNORECASE); message = re.sub(r'^(?:ERROR|WARNING|INFO|DEBUG|FATAL|CRITICAL)\s*[:\-]\s*', '', message, flags=re.IGNORECASE); message = message.replace('!!!! Warning: Station', 'Station').replace('!!!! Warning:  - Fault: ', 'Fault: '); message = re.sub(r'in\s+[\/\w\.\-]+\s*:\s*', '', message); message = re.sub(r'0x[0-9a-fA-F]+\b', '', message); message = re.sub(r': None$', '', message)
    return category, message.strip()

def _process_log_file(file_path):
    # (Code unverändert)
    filename = os.path.basename(file_path); entries = []; skipped_count = 0; current_year_for_file = str(datetime.now().year)
    try:
        for enc in ['utf-8', 'latin1', 'cp1252']:
            try:
                line_count_for_file = 0; skipped_within_encoding = 0
                with open(file_path, 'r', encoding=enc) as f:
                    for line in f:
                        line_count_for_file += 1; line = line.strip()
                        if not line: continue
                        timestamp, _ = _parse_timestamp_static(line, current_year_for_file)
                        if timestamp is None: skipped_within_encoding += 1; continue
                        category, clean_message = _categorize_and_clean_message_static(line, filename, current_year_for_file)
                        if not category: continue
                        entries.append({'Timestamp': timestamp, 'SourceFile': filename, 'Severity': category, 'Event': clean_message, 'OriginalLog': line})
                skipped_count = skipped_within_encoding; break
            except UnicodeDecodeError: continue
            except Exception as read_err: print(f"INFO: Fehler Lesen {filename} mit {enc}: {read_err}", file=sys.stderr); break
    except Exception as e: print(f"FEHLER: Datei {filename} nicht verarbeitbar: {e}", file=sys.stderr)
    return filename, entries, skipped_count


class SystemAnalyzerApp:
    # ... (__init__ und _setup_ui bleiben unverändert) ...
    def __init__(self, parent):
        self.parent = parent; self.parent.title("Eigenständige System-Analyse (ClearScan)"); self.parent.geometry("1200x750")
        try: import sv_ttk; sv_ttk.set_theme("dark")
        except Exception: pass
        style = ttk.Style(self.parent); style.map('Treeview', background=[('selected', '#343434')], foreground=[('selected', 'white')])
        try: default_font = tkfont.nametofont("TkDefaultFont"); self.bold_font = default_font.copy(); self.bold_font.configure(weight="bold"); style.configure("Critical.Treeview", font=self.bold_font, foreground="red")
        except tk.TclError: self.bold_font = None
        self.raw_df = pd.DataFrame(); self.incidents_df = pd.DataFrame(); self.filtered_incidents_df = pd.DataFrame(); self.loading_win = None
        self._setup_ui()

    def _setup_ui(self):
        main_frame = ttk.Frame(self.parent, padding="10"); main_frame.pack(fill=tk.BOTH, expand=True)
        control_frame = ttk.Frame(main_frame); control_frame.pack(fill=tk.X, pady=5)
        ttk.Button(control_frame, text="Log-Ordner analysieren", command=self._start_analysis_from_dialog).pack(side=tk.LEFT, padx=5, pady=5)
        self.filter_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Nur letzte 2 Tage (relativ)", variable=self.filter_var).pack(side=tk.LEFT, padx=(15, 5))
        filter_frame = ttk.Frame(main_frame); filter_frame.pack(fill=tk.X, pady=(5,0), padx=5)
        ttk.Label(filter_frame, text="Filtern nach:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(filter_frame, text="Stufe:").pack(side=tk.LEFT, padx=(0, 5))
        self.severity_filter_combo = ttk.Combobox(filter_frame, state="readonly", width=10, values=['Alle', 'Fatal', 'Error', 'Warning', 'Info', 'Restart', 'Connection', 'Hardware', 'Startup', 'License', 'Config'])
        self.severity_filter_combo.pack(side=tk.LEFT, padx=5); self.severity_filter_combo.set('Alle')
        self.severity_filter_combo.bind("<<ComboboxSelected>>", self._apply_filters)
        ttk.Label(filter_frame, text="Datei:").pack(side=tk.LEFT, padx=(10, 5))
        self.source_filter_combo = ttk.Combobox(filter_frame, state="readonly", width=25)
        self.source_filter_combo.pack(side=tk.LEFT, padx=5); self.source_filter_combo.set('Alle')
        self.source_filter_combo.bind("<<ComboboxSelected>>", self._apply_filters)
        ttk.Label(filter_frame, text="Datum:").pack(side=tk.LEFT, padx=(10, 5))
        self.date_filter_combo = ttk.Combobox(filter_frame, state="readonly", width=15)
        self.date_filter_combo.pack(side=tk.LEFT, padx=5)
        self.date_filter_combo.bind("<<ComboboxSelected>>", self._apply_filters)
        ttk.Button(filter_frame, text="Alle Filter zurücksetzen", command=self._reset_all_filters).pack(side=tk.LEFT, padx=15)
        log_frame = ttk.LabelFrame(main_frame, text="Gefundene System-Ereignisse", padding=10); log_frame.pack(fill=tk.BOTH, expand=True, pady=(10,0))
        self.tree = ttk.Treeview(log_frame, columns=("Timestamp", "Severity", "SourceFile", "Event"), show="headings")
        self.tree.heading("Timestamp", text="Zeitpunkt"); self.tree.column("Timestamp", width=150, anchor="w")
        self.tree.heading("Severity", text="Stufe"); self.tree.column("Severity", width=80, anchor="center")
        self.tree.heading("SourceFile", text="Quelldatei", anchor="w"); self.tree.column("SourceFile", width=200, anchor="w")
        self.tree.heading("Event", text="Ereignis"); self.tree.column("Event", width=650)
        self.tree.bind("<Double-1>", self._on_item_select)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set); scrollbar.pack(side=tk.RIGHT, fill=tk.Y); self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.tag_configure("Fatal", foreground="#FF5252", font=self.bold_font if self.bold_font else None); self.tree.tag_configure("Error", foreground="#FF8A80"); self.tree.tag_configure("Warning", foreground="#FFD180"); self.tree.tag_configure("Info", foreground="#80CBC4"); self.tree.tag_configure("Restart", foreground="#8C9EFF"); self.tree.tag_configure("Connection", foreground="#FF8A80"); self.tree.tag_configure("Hardware", foreground="#FF8A80"); self.tree.tag_configure("Startup", foreground="#FF8A80"); self.tree.tag_configure("License", foreground="#FFD180"); self.tree.tag_configure("Config", foreground="#FFD180")
        status_bar = ttk.Frame(self.parent, padding=(5, 2)); status_bar.pack(side=tk.BOTTOM, fill=tk.X); self.status_label = ttk.Label(status_bar, text="Bereit."); self.status_label.pack(side=tk.LEFT, padx=5)

    def _start_analysis_from_dialog(self):
        # ... (remains the same) ...
        dir_path = filedialog.askdirectory(title="Wählen Sie den Log-Ordner zur System-Analyse")
        if not dir_path: return
        self._create_loading_window()
        filter_enabled = self.filter_var.get()
        thread = threading.Thread(target=self._run_analysis_thread_safe, args=(dir_path, filter_enabled), daemon=True)
        thread.start()

    def _run_analysis_thread_safe(self, dir_path, filter_relatively):
        # ... (remains the same) ...
        try: self._run_analysis_thread(dir_path, filter_relatively)
        except Exception as e:
            print(f"FATALER FEHLER im Analyse-Thread:\n{traceback.format_exc()}", file=sys.stderr)
            self.parent.after(0, self._finalize_analysis, False, f"Schwerer Fehler: {e}")

    # --- UPDATED _run_analysis_thread ---
    def _run_analysis_thread(self, dir_path, filter_relatively=False):
        """Main analysis logic: find files, filter by date (optional), copy, analyze."""
        def progress_callback(progress, message):
             if self.loading_win: self.parent.after(0, self._update_progress, progress, message)

        # --- PHASE 1: Find ALL potential files and determine latest date ---
        progress_callback(0, "Durchsuche Verzeichnis...")
        potential_files = [] # Stores tuple: (full_path, file_date or None)
        names_to_exclude = ['abyss', 'anaconda', 'baddet', 'detpos', 'filtetdet', 'monitor_replication']
        files_to_exclude_general = ['yum.log', 'oms.log', 'scanner_bag.log', 'app.log']
        filename_date_pattern = re.compile(r'(\d{4}-\d{2}-\d{2})') # YYYY-MM-DD
        latest_log_date = None # Store as date object

        for root, _, files in os.walk(dir_path):
            for file in files:
                filename = os.path.basename(file); filename_lower = filename.lower()
                base_name, ext = os.path.splitext(filename_lower)

                # Apply Exclusions
                if filename_lower.endswith(('.img', 'svr.log')) or ('verbose' in filename_lower and ext == '.csv'): continue
                if filename_lower in files_to_exclude_general or filename_lower.startswith('alg'): continue
                if base_name in names_to_exclude: continue

                # Check Eligibility
                has_extension = ext != ''
                is_log_file = ext in ['.log', '.csv']
                is_known_no_ext = not has_extension and any(filename_lower.startswith(p) for p in ['dcs_', 'diagserv_', 'scs_', 'syserror_', 'current'])

                if is_log_file or is_known_no_ext:
                    full_path = os.path.join(root, file)
                    file_date = None # Date object or None
                    date_match = filename_date_pattern.search(filename)
                    if date_match:
                        try:
                            file_date = datetime.strptime(date_match.group(1), '%Y-%m-%d').date()
                            if latest_log_date is None or file_date > latest_log_date:
                                latest_log_date = file_date
                        except ValueError: pass # Invalid date format in name
                    potential_files.append((full_path, file_date)) # Store path and date

        if not potential_files:
            self.parent.after(0, self._finalize_analysis, False, "Keine relevanten Log-Dateien gefunden."); return

        # --- PHASE 2: Filter file list based on relative date ---
        original_log_files = [] # Files to actually process
        msg_suffix = "."

        if filter_relatively and latest_log_date:
            date_limit = latest_log_date - timedelta(days=2) # Date object
            msg_suffix = f" (letzte 2 Tage relativ zu {latest_log_date.strftime('%Y-%m-%d')})."
            progress_callback(10, f"Filtere Dateien bis {date_limit.strftime('%Y-%m-%d')}...")
            files_kept_count = 0
            for file_path, file_date in potential_files:
                if file_date is None: # Keep files without a date
                    original_log_files.append(file_path)
                    files_kept_count += 1
                elif file_date >= date_limit: # Keep files within the date range
                    original_log_files.append(file_path)
                    files_kept_count += 1
            print(f"Datumsfilter: {files_kept_count} von {len(potential_files)} Dateien behalten.")
            if not original_log_files:
                 self.parent.after(0, self._finalize_analysis, False, f"Keine Logs im Datumsfenster gefunden{msg_suffix}."); return

        elif filter_relatively: # Filter on, but no dated files found
             print("WARNUNG: Relativer Datumsfilter aktiv, aber keine Daten in Dateinamen gefunden. Analysiere alle.")
             original_log_files = [f[0] for f in potential_files] # Get paths only
             msg_suffix = " (keine Datumsangaben in Dateinamen gefunden)."
        else: # Filter off
            original_log_files = [f[0] for f in potential_files] # Get paths only

        # --- PHASE 3: Copying ---
        # (Code remains the same as previous version)
        copied_log_files = []
        try:
            analysis_start_time_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            base_log_dir = os.path.join(os.getcwd(), "logs", "system_analysis"); dest_dir = os.path.join(base_log_dir, f"analysis_{analysis_start_time_str}")
            if os.path.exists(dest_dir): shutil.rmtree(dest_dir)
            os.makedirs(dest_dir, exist_ok=True); print(f"Kopiere {len(original_log_files)} Logs nach: {dest_dir}")
            base_progress = 10; progress_callback(base_progress, "Kopiere Logs...")
            total_files_to_copy = len(original_log_files)
            for i, src_path in enumerate(original_log_files):
                try:
                    dest_path = os.path.join(dest_dir, os.path.basename(src_path)); shutil.copy2(src_path, dest_path); copied_log_files.append(dest_path)
                    progress = base_progress + int(((i + 1) / total_files_to_copy) * 40)
                    progress_callback(progress, f"Kopiere: {os.path.basename(src_path)}")
                except Exception as copy_err: print(f"WARNUNG: Kopieren fehlgeschlagen {src_path}: {copy_err}", file=sys.stderr)
            if not copied_log_files: self.parent.after(0, self._finalize_analysis, False, "Keine Dateien kopiert."); return
            progress_callback(50, f"{len(copied_log_files)} Dateien kopiert. Starte Analyse...")
        except Exception as e: print(f"FEHLER Ordner/Kopieren:\n{traceback.format_exc()}", file=sys.stderr); self.parent.after(0, self._finalize_analysis, False, f"Fehler Kopieren: {e}"); return

        # --- PHASE 4: ANALYSIS ---
        # (Code remains the same as previous version)
        all_entries = []; total_files_to_analyze = len(copied_log_files); processed_files_count = 0; total_skipped_lines = 0
        num_processes = max(1, multiprocessing.cpu_count() - 1); print(f"Starte Analyse mit {num_processes} Prozessen...")
        try:
             ctx = multiprocessing.get_context('spawn')
             with ctx.Pool(processes=num_processes) as pool:
                 results_iterator = pool.imap_unordered(_process_log_file, copied_log_files)
                 for filename, file_entries, skipped_count in results_iterator:
                     if file_entries: all_entries.extend(file_entries)
                     total_skipped_lines += skipped_count; processed_files_count += 1
                     progress = 50 + int((processed_files_count / total_files_to_analyze) * 50)
                     progress_callback(progress, f"Analysiere: {filename} ({processed_files_count}/{total_files_to_analyze})")
             print("Multiprocessing Pool beendet.")
        except Exception as pool_err: print(f"FEHLER Multiprocessing:\n{traceback.format_exc()}", file=sys.stderr); self.parent.after(0, self._finalize_analysis, False, f"Pool Fehler: {pool_err}"); return
        if total_skipped_lines > 0: print(f"WARNUNG: {total_skipped_lines} Zeilen übersprungen (Zeitstempel).")
        if not all_entries: msg = "Keine relevanten Ereignisse gefunden."; msg += f" ({total_skipped_lines} Zeilen übersprungen)" if total_skipped_lines > 0 else ""; self.parent.after(0, self._finalize_analysis, False, msg); return

        # --- PHASE 5: DataFrame Creation ---
        # (Code remains the same as previous version - NO date filtering needed here anymore)
        progress_callback(100, "Erstelle DataFrame...")
        self.raw_df = pd.DataFrame(all_entries); self.raw_df['Timestamp'] = pd.to_datetime(self.raw_df['Timestamp'], errors='coerce')
        self.raw_df.dropna(subset=['Timestamp'], inplace=True)
        if self.raw_df.empty: self.parent.after(0, self._finalize_analysis, False, "Keine gültigen Zeitstempel gefunden."); return
        self.raw_df.sort_values(by="Timestamp", inplace=True); self.raw_df.reset_index(drop=True, inplace=True)

        # incidents_df now holds ALL results found within the FILE date filter
        self.incidents_df = self.raw_df.copy()
        # Reset index for incidents_df as well (good practice)
        self.incidents_df.reset_index(drop=True, inplace=True)
        self.filtered_incidents_df = self.incidents_df.copy()

        final_msg = f"{len(self.incidents_df)} Ereignisse gefunden{msg_suffix}"; final_msg += f" ({total_skipped_lines} Zeilen übersprungen)" if total_skipped_lines > 0 else ""
        self.parent.after(0, self._finalize_analysis, True, final_msg)


    # --- Methods below remain unchanged ---
    # _finalize_analysis, _populate_filters, _apply_filters, _reset_all_filters
    # _update_treeview, _on_item_select, _create_loading_window, _update_progress

    def _finalize_analysis(self, success, message):
        if self.loading_win: self.loading_win.destroy(); self.loading_win = None
        if not success:
            messagebox.showwarning("Analyse fehlgeschlagen", message, parent=self.parent)
            self.raw_df = pd.DataFrame(); self.incidents_df = pd.DataFrame(); self.filtered_incidents_df = pd.DataFrame()
            self._update_treeview(pd.DataFrame()); self._populate_filters()
            return
        self.filtered_incidents_df = self.incidents_df.copy() # Ensure filtered starts fresh
        self._populate_filters()
        self._apply_filters()
        self.status_label.config(text=message)
        simple_message = message.split("(")[0].strip()
        messagebox.showinfo("System-Analyse abgeschlossen", simple_message, parent=self.parent)

    def _populate_filters(self):
        self.severity_filter_combo.set('Alle'); self.date_filter_combo.set(''); self.source_filter_combo.set('Alle')
        self.source_filter_combo['values'] = ['Alle']; self.date_filter_combo['values'] = []
        # Use incidents_df for populating filters, as it contains the base data for the run
        base_df_for_filters = self.incidents_df
        if base_df_for_filters.empty: return
        if 'SourceFile' in base_df_for_filters.columns:
            unique_sources = sorted(base_df_for_filters['SourceFile'].unique())
            if unique_sources: self.source_filter_combo['values'] = ['Alle'] + unique_sources
        if 'Timestamp' in base_df_for_filters.columns:
            valid_dates = base_df_for_filters['Timestamp'].dropna()
            if not valid_dates.empty:
                unique_dates = sorted(valid_dates.dt.date.unique(), reverse=True)
                self.date_filter_combo['values'] = [d.strftime('%Y-%m-%d') for d in unique_dates]

    def _apply_filters(self, event=None):
        if self.incidents_df.empty: self._update_treeview(pd.DataFrame()); self.status_label.config(text="Keine Daten."); return
        df_to_filter = self.incidents_df.copy() # Always start filtering from the full result set for this run
        selected_severity = self.severity_filter_combo.get(); selected_source = self.source_filter_combo.get(); selected_date_str = self.date_filter_combo.get()
        if selected_severity and selected_severity != 'Alle': df_to_filter = df_to_filter[df_to_filter['Severity'] == selected_severity]
        if selected_source and selected_source != 'Alle': df_to_filter = df_to_filter[df_to_filter['SourceFile'] == selected_source]
        if selected_date_str:
            try: selected_date = pd.to_datetime(selected_date_str).date(); df_to_filter = df_to_filter[df_to_filter['Timestamp'].dt.date == selected_date]
            except (ValueError, AttributeError): pass
        self.filtered_incidents_df = df_to_filter; self._update_treeview(self.filtered_incidents_df)
        self.status_label.config(text=f"{len(self.filtered_incidents_df)} Ereignisse nach Filterung.")

    def _reset_all_filters(self):
        self.severity_filter_combo.set('Alle'); self.source_filter_combo.set('Alle'); self.date_filter_combo.set('')
        self._apply_filters()

    def _update_treeview(self, df_to_show):
        for i in self.tree.get_children(): self.tree.delete(i)
        if df_to_show is None or df_to_show.empty: return
        for index, row in df_to_show.iterrows():
            tag = row['Severity'] if pd.notna(row['Severity']) else ''
            # Use the DataFrame index (which is now stable after reset_index) as iid
            self.tree.insert("", "end", iid=index, tags=(tag,), values=(
                                row['Timestamp'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['Timestamp']) else 'N/A',
                                row['Severity'], row['SourceFile'], row['Event'] ))

    def _on_item_select(self, event):
        selected_item_iid = self.tree.focus();
        if not selected_item_iid: return
        try:
            # iid is the index of filtered_incidents_df
            selected_display_row = self.filtered_incidents_df.loc[int(selected_item_iid)]
            # Match in raw_df using unique info
            timestamp_match = selected_display_row['Timestamp']
            original_log_match = selected_display_row['OriginalLog']
            source_file_match = selected_display_row['SourceFile']
            potential_matches = self.raw_df[ (self.raw_df['Timestamp'] == timestamp_match) & (self.raw_df['OriginalLog'] == original_log_match) & (self.raw_df['SourceFile'] == source_file_match) ]
            if not potential_matches.empty:
                selected_raw_row = self.raw_df.loc[potential_matches.index[0]]
                GateViewCasefileWindow(self.parent, selected_raw_row, self.raw_df)
            else: messagebox.showwarning("Fehler", "Rohdaten-Eintrag nicht gefunden.", parent=self.parent)
        except (ValueError, KeyError, AttributeError, IndexError) as e:
             print(f"Fehler Öffnen Detailfenster (IID: {selected_item_iid}): {e}\n{traceback.format_exc()}")
             messagebox.showwarning("Fehler", "Detailansicht nicht möglich.", parent=self.parent)

    def _create_loading_window(self):
        # ... (same as before) ...
        self.loading_win = tk.Toplevel(self.parent); self.loading_win.title("Ladevorgang"); self.loading_win.geometry("450x130"); self.loading_win.resizable(False, False); self.parent.update_idletasks(); x = self.parent.winfo_screenwidth() // 2 - self.loading_win.winfo_width() // 2; y = self.parent.winfo_screenheight() // 2 - self.loading_win.winfo_height() // 2; self.loading_win.geometry(f"+{x}+{y}"); self.loading_win.transient(self.parent); self.loading_win.grab_set(); self.loading_label = ttk.Label(self.loading_win, text="Initialisiere...", font=("Helvetica", 10)); self.loading_label.pack(pady=(15, 5), padx=10, anchor="w"); self.loading_progress_bar = ttk.Progressbar(self.loading_win, orient="horizontal", mode="determinate"); self.loading_progress_bar.pack(fill=tk.X, expand=True, padx=10); self.percent_label = ttk.Label(self.loading_win, text="0%", font=("Helvetica", 10)); self.percent_label.pack(pady=5)

    def _update_progress(self, progress, filename):
        # ... (same as before) ...
        if self.loading_win:
             try: self.loading_win.lift(); self.loading_label.config(text=f"{filename}"); self.loading_progress_bar['value'] = progress; self.percent_label.config(text=f"{progress}%"); self.loading_win.update_idletasks()
             except tk.TclError: pass

if __name__ == "__main__":
    multiprocessing.freeze_support() # Keep this here!
    root = tk.Tk()
    app = SystemAnalyzerApp(root)
    root.mainloop()