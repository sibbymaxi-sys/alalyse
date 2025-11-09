# mv3d_system_analyzer_app.py
# (KORRIGIERT: BaseApp-Import, Syntax-Fix, nutzt ERROR_DEFINITIONS, UI aus Original)

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, font as tkfont
import pandas as pd
import threading
import os
import re
import sys
import traceback
import multiprocessing
from multiprocessing import Pool # Expliziter Import
from datetime import datetime, timedelta, date
import shutil
from log_previewer import get_log_file_daterange_and_count

# Importiere DateEntry
try:
    from tkcalendar import DateEntry
except ImportError:
    messagebox.showerror("Fehlende Bibliothek", "Das Paket 'tkcalendar' wird benötigt.\nBitte installieren Sie es mit: pip install tkcalendar")
    sys.exit(1)

# --- Imports für MV3D SYSTEM Analyse ---
# WICHTIG: Importiere BaseApp ZUERST
try:
    from base_app import BaseApp # Erbt von BaseApp
except ImportError as e:
    print(f"FATAL: Importfehler in mv3d_system_analyzer_app (BaseApp): {e}\n{traceback.format_exc()}")
    try: root_err = tk.Tk(); root_err.withdraw(); messagebox.showerror("Kritischer Import Fehler", f"BaseApp nicht gefunden:\n{e}")
    except Exception: pass
    sys.exit(1)

try:
    # Verwende die Variable aus deiner hochgeladenen Datei
    from help_texts import MV3D_HELP_TEXT 
except ImportError:
    print("WARNUNG: help_texts.py nicht gefunden. Standard-Hilfetext wird verwendet.")
    MV3D_HELP_TEXT = "Keine spezifische Hilfe für MV3D System Analyzer gefunden."

try:
    from mv3d_casefile_window import MV3DCasefileWindow
except ImportError:
    print("WARNUNG: mv3d_casefile_window.py nicht gefunden. Detailansicht deaktiviert.")
    class MV3DCasefileWindow: # Fallback (korrekt eingerückt)
        def __init__(self, parent, selected_row, raw_df):
            messagebox.showerror("Fehler", "Detailfenster (mv3d_casefile_window.py) nicht geladen.", parent=parent)
            win = tk.Toplevel(parent); win.title("Fehler"); ttk.Label(win, text="Detailfenster nicht geladen.").pack(padx=20, pady=20)



# --- KORREKTER IMPORT: Nutze das Dictionary aus deiner Definitions-Datei ---
try:
    from mv3d_error_definitions import ERROR_DEFINITIONS
except ImportError:
    print("WARNUNG: mv3d_error_definitions.py nicht gefunden. Fehler werden nicht hervorgehoben.")
    ERROR_DEFINITIONS = {} # Leeres Dict als Fallback

# --- OPTIMIERUNG (BESCHLEUNIGUNG): Regex vorkompilieren ---
COMPILED_ERROR_PATTERNS = []
try:
    for pattern_str, details in ERROR_DEFINITIONS.items():
        try:
            # Bestimme Kategorie basierend auf Keywords
            category = "Unknown" # Default
            if "FATAL" in pattern_str.upper() or "E-STOP" in pattern_str.upper(): category = "Fatal"
            elif "ERROR" in pattern_str.upper() or "FAIL" in pattern_str.upper() or "FAULT" in pattern_str.upper(): category = "Error"
            elif "WARN" in pattern_str.upper(): category = "Warning"
            
            compiled_pattern = re.compile(pattern_str, re.IGNORECASE)
            COMPILED_ERROR_PATTERNS.append((compiled_pattern, category)) # Speichere (Pattern, Kategorie)
        except re.error as e:
            print(f"FEHLER: Ungültiges Regex in mv3d_error_definitions.py (wird ignoriert): '{pattern_str}' -> {e}")
except Exception as e:
    print(f"FEHLER beim Kompilieren der ERROR_DEFINITIONS: {e}")
print(f"--- {len(COMPILED_ERROR_PATTERNS)} MV3D-Fehlermuster vorkompiliert. ---")
# --- ENDE OPTIMIERUNG ---



# === Helper Functions (Angepasst für MV3D System-Analyse) ===

# --- KORRIGIERTER TIMESTAMP PARSER (Syntax-Fix im Fallback) ---
def _parse_timestamp_static_mv3d(line, year_str):
    line_cleaned = re.sub(r'^[a-zA-Z\._]+:\s*', '', line); year = int(year_str) if year_str.isdigit() else datetime.now().year
    patterns = [
        (r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\.\d{2}\.\d{3})', '%Y-%m-%d %H:%M.%S.%f', False),
        (r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,\.]\d{3})', '%Y-%m-%d %H:%M:%S.%f', False),
        (r'^([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)', '%a %b %d %H:%M:%S.%f', True), # Aus mv3d_log_parser
        (r'^(\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})(?!\.\d)', '%a %b %d %H:%M:%S', True),
        (r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)', 'iso', False),
    ]
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
                    ts_str_no_ms = ts_str_clean.split('.')[0]; fmt_no_ms = fmt.split('.')[0]
                    try: dt = pd.to_datetime(f"{ts_str_no_ms} {year}", format=f"{fmt_no_ms} %Y")
                    except ValueError:
                         try: dt = pd.to_datetime(f"{ts_str_no_ms} {year-1}", format=f"{fmt_no_ms} %Y")
                         except ValueError: continue
                else: dt = pd.to_datetime(ts_str_clean, format=fmt)
                if pd.notna(dt): return dt, end_pos
            except ValueError: continue
    # --- KORRIGIERTER FALLBACK BLOCK (Syntax-Fix) ---
    try:
        dt_fallback = pd.to_datetime(line, errors='coerce', infer_datetime_format=True)
        if pd.notna(dt_fallback):
             if dt_fallback.year < 1970:
                 try: dt_fallback = dt_fallback.replace(year=year)
                 except ValueError: pass
             return dt_fallback, None
    except Exception as e:
        pass # KORREKTE EINRÜCKUNG
    return None, None
# --- ENDE KORRIGIERTER TIMESTAMP PARSER ---

# --- KORRIGIERTER KATEGORISIERER (nutzt ERROR_DEFINITIONS) ---
def _categorize_and_clean_message_static_mv3d(original_line, filename, year_str):
    """Kategorisiert Zeile basierend auf ERROR_DEFINITIONS und Fallbacks."""
    # 1. Spezifische Definitionen (nutzt das importierte Dictionary)
    for pattern_str, details in ERROR_DEFINITIONS.items():
        try:
            if re.search(pattern_str, original_line, re.IGNORECASE):
                # Bestimme Kategorie basierend auf Keywords (deine Logik)
                category = "Unknown" # Default
                if "FATAL" in pattern_str.upper() or "E-STOP" in pattern_str.upper(): category = "Fatal"
                elif "ERROR" in pattern_str.upper() or "FAIL" in pattern_str.upper() or "FAULT" in pattern_str.upper(): category = "Error"
                elif "WARN" in pattern_str.upper(): category = "Warning"
                
                message = original_line
                _, msg_start = _parse_timestamp_static_mv3d(message, year_str)
                if msg_start is not None and msg_start < len(message): message = message[msg_start:].strip()
                message = re.sub(r'^\[.*?\]\s*:\s*', '', message)
                message = re.sub(r'^(?:ERROR|WARNING|INFO|DEBUG|FATAL|CRITICAL)\s*[:\-]\s*', '', message, flags=re.IGNORECASE)
                # print(f"    +++ DEF HIT! Cat={category}, Msg={message.strip()} (File: {filename})") # DEBUG
                return category, message.strip()
        except re.error:
            print(f"WARNUNG: Ungültiges Regex in mv3d_error_definitions.py: {pattern_str}")
            continue

    # 2. Generischer Fallback (deine Logik aus dem Original)
    line_lower = original_line.lower()
    category = None
    if any(kw in line_lower for kw in ['fatal', 'critical', 'exception', 'panic', 'core dumped', 'traceback', 'assert']): category = "Fatal"
    elif any(kw in line_lower for kw in ['e-stop', 'estop']): category = "E-Stop"
    elif any(kw in line_lower for kw in ['hvps']): category = "HVPS"
    elif any(kw in line_lower for kw in ['bag jam', 'bagjam']): category = "BagJam"
    elif any(kw in line_lower for kw in ['license']): category = "License"
    elif 'error' in line_lower: category = "Error"
    elif 'warn' in line_lower: category = "Warning"
    elif 'fail' in line_lower: category = "Error"
    elif 'fault' in line_lower: category = "Error"
    
    if not category: return None, None # Kein Treffer

    # print(f"    *** FALLBACK HIT! Cat={category}, Line: {original_line[:80]}... (File: {filename})") # DEBUG
    # Nachricht bereinigen
    message = original_line
    _, msg_start = _parse_timestamp_static_mv3d(message, year_str)
    if msg_start is not None and msg_start < len(message): message = message[msg_start:].strip()
    message = re.sub(r'^\[.*?\]\s*:\s*', '', message)
    message = re.sub(r'^(?:ERROR|WARNING|INFO|DEBUG|FATAL|CRITICAL)\s*[:\-]\s*', '', message, flags=re.IGNORECASE)
    return category, message.strip()

# === Worker Function ===
def _process_log_file_mv3d(file_path):
    """Worker-Funktion für Multiprocessing."""
    filename = os.path.basename(file_path); entries = []; skipped_count = 0; current_year_for_file = str(datetime.now().year)
    # print(f"--- Worker processing (MV3D System): {filename} ---") # DEBUG
    lines_read = 0; lines_categorized = 0; lines_with_ts = 0
    try:
        normalized_path = os.path.normpath(file_path)
        if not os.path.exists(normalized_path):
             print(f"WARNUNG (Worker): Datei existiert nicht mehr: {normalized_path}", file=sys.stderr)
             return filename, [], 0
        for enc in ['utf-8', 'latin1', 'cp1252']:
            try:
                line_count_for_file = 0; skipped_within_encoding = 0
                with open(normalized_path, 'r', encoding=enc) as f:
                    for line_num, line in enumerate(f):
                        line_count_for_file += 1; lines_read += 1; line = line.strip();
                        if not line: continue
                        timestamp, _ = _parse_timestamp_static_mv3d(line, current_year_for_file)
                        if timestamp is None: skipped_within_encoding += 1; continue
                        lines_with_ts += 1
                        category, clean_message = _categorize_and_clean_message_static_mv3d(line, filename, current_year_for_file)
                        if category:
                            lines_categorized += 1
                            entries.append({'Timestamp': timestamp, 'SourceFile': filename, 'Severity': category, 'Event': clean_message, 'OriginalLog': line})
                skipped_count = skipped_within_encoding;
                # print(f"--- Worker finished {filename} ({enc}): Read={line_count_for_file}, TS OK={lines_with_ts}, Skip(TS)={skipped_count}, Cat={lines_categorized}, Found={len(entries)} ---") # DEBUG
                break
            except UnicodeDecodeError: continue
            except FileNotFoundError: print(f"WARNUNG (Worker): Datei beim Lesen nicht gefunden: {normalized_path}", file=sys.stderr); skipped_count = line_count_for_file if 'line_count_for_file' in locals() else 0; break
            except Exception as read_err: print(f"INFO: Fehler Lesen {filename} mit {enc}: {read_err}", file=sys.stderr); break
    except Exception as e: print(f"FEHLER: Datei {filename} nicht verarbeitbar: {e}", file=sys.stderr)
    return filename, entries, skipped_count


# === Main Application Class ===
class MV3DSystemAnalyzerApp(BaseApp):
    def __init__(self, parent, incidents_df=None, raw_df=None, *args, **kwargs): # HINZUFÜGEN: incidents_df und raw_df
        super().__init__(parent, app_name="MV3D System Analyzer", version="1.0")
        
        # KORREKTUR: Verwende die übergebenen Daten, WENN sie existieren.
        self.raw_df = raw_df if raw_df is not None and not raw_df.empty else pd.DataFrame()
        self.incidents_df = incidents_df if incidents_df is not None and not incidents_df.empty else pd.DataFrame()
        self.filtered_incidents_df = self.incidents_df.copy() # Wichtig: Kopie erstellen
        self.loading_win = None
        
        self._setup_ui()
        
        # NEU: Wenn Daten übergeben wurden, fülle sofort die Ansicht
        if not self.incidents_df.empty:
            self.after(100, self._populate_and_filter_on_load) # kleiner Delay für UI-Aufbau

    def _populate_and_filter_on_load(self):
        """Hilfsfunktion, um die UI nach dem Laden zu füllen."""
        try:
            self._populate_filters()
            self._apply_filters()
            self.status_label.config(text=f"{len(self.incidents_df)} Ereignisse aus Hauptfenster geladen.")
        except Exception as e:
            print(f"Fehler beim initialen Füllen der UI: {e}")
            self.status_label.config(text="Fehler beim Laden der Filter.")

    def _setup_ui(self):
        # --- UI BASIEREND AUF DEINEM ORIGINAL ---
        main_frame = ttk.Frame(self, padding="10"); main_frame.pack(fill=tk.BOTH, expand=True)
        control_frame = ttk.Frame(main_frame); control_frame.pack(fill=tk.X, pady=5)
        ttk.Button(control_frame, text="MV3D Log-Ordner analysieren", command=self._start_analysis_from_dialog).pack(side=tk.LEFT, padx=5, pady=5)
        self.filter_var = tk.BooleanVar(value=True) # Zeitfilter Checkbox
        ttk.Checkbutton(control_frame, text="Nur letzte 2 Tage (relativ)", variable=self.filter_var).pack(side=tk.LEFT, padx=(15, 5))
        filter_frame1 = ttk.Frame(main_frame); filter_frame1.pack(fill=tk.X, pady=(5, 2), padx=5)
        ttk.Label(filter_frame1, text="Suchen (Log):").pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = ttk.Entry(filter_frame1, width=30); self.search_entry.pack(side=tk.LEFT, padx=5); self.search_entry.bind("<Return>", self._apply_filters)
        ttk.Label(filter_frame1, text="Fehlercode (Regex):").pack(side=tk.LEFT, padx=(10, 5))
        self.errorcode_entry = ttk.Entry(filter_frame1, width=20); self.errorcode_entry.pack(side=tk.LEFT, padx=5); self.errorcode_entry.bind("<Return>", self._apply_filters)
        ttk.Label(filter_frame1, text="Datei:").pack(side=tk.LEFT, padx=(10, 5))
        self.source_filter_combo = ttk.Combobox(filter_frame1, state="readonly", width=25)
        self.source_filter_combo.pack(side=tk.LEFT, padx=5); self.source_filter_combo.set('Alle'); self.source_filter_combo.bind("<<ComboboxSelected>>", self._apply_filters)
        filter_frame2 = ttk.Frame(main_frame); filter_frame2.pack(fill=tk.X, pady=(2, 5), padx=5)
        ttk.Label(filter_frame2, text="Fehler-Typen:").pack(side=tk.LEFT, padx=(0, 5))
        self.estop_var = tk.BooleanVar(value=False); ttk.Checkbutton(filter_frame2, text="E-Stop", variable=self.estop_var, command=self._apply_filters).pack(side=tk.LEFT, padx=2)
        self.hvps_var = tk.BooleanVar(value=False); ttk.Checkbutton(filter_frame2, text="HVPS", variable=self.hvps_var, command=self._apply_filters).pack(side=tk.LEFT, padx=2)
        self.bagjam_var = tk.BooleanVar(value=False); ttk.Checkbutton(filter_frame2, text="Bag Jam", variable=self.bagjam_var, command=self._apply_filters).pack(side=tk.LEFT, padx=2)
        self.license_var = tk.BooleanVar(value=False); ttk.Checkbutton(filter_frame2, text="License", variable=self.license_var, command=self._apply_filters).pack(side=tk.LEFT, padx=2)
        ttk.Label(filter_frame2, text="Stufe:").pack(side=tk.LEFT, padx=(10, 5))
        self.severity_filter_combo = ttk.Combobox(filter_frame2, state="readonly", width=10, values=['Alle', 'Fatal', 'Error', 'Warning', 'Info', 'Connection', 'Hardware', 'E-Stop', 'HVPS', 'BagJam', 'License', 'Startup'])
        self.severity_filter_combo.pack(side=tk.LEFT, padx=5); self.severity_filter_combo.set('Alle'); self.severity_filter_combo.bind("<<ComboboxSelected>>", self._apply_filters)
        ttk.Label(filter_frame2, text="Datum:").pack(side=tk.LEFT, padx=(10, 5))
        self.date_filter_combo = DateEntry(filter_frame2, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd') # DateEntry
        self.date_filter_combo.pack(side=tk.LEFT, padx=5); self.date_filter_combo.set_date(None);
        self.date_filter_combo.bind("<<DateEntrySelected>>", self._apply_filters)
        ttk.Button(filter_frame2, text="Alle Filter zurücksetzen", command=self._reset_all_filters).pack(side=tk.LEFT, padx=15)
        # --- ENDE UI WIEDERHERGESTELLT ---

        log_frame = ttk.LabelFrame(main_frame, text="Gefundene System-Ereignisse", padding=10); log_frame.pack(fill=tk.BOTH, expand=True, pady=(5,0))
        self.tree = ttk.Treeview(log_frame, columns=("Timestamp", "Severity", "SourceFile", "Event"), show="headings")
        self.tree.heading("Timestamp", text="Zeitpunkt"); self.tree.column("Timestamp", width=150, anchor="w"); self.tree.heading("Severity", text="Stufe"); self.tree.column("Severity", width=80, anchor="center"); self.tree.heading("SourceFile", text="Quelldatei", anchor="w"); self.tree.column("SourceFile", width=200, anchor="w"); self.tree.heading("Event", text="Ereignis"); self.tree.column("Event", width=650)
        self.tree.bind("<Double-1>", self._on_item_select)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set); scrollbar.pack(side=tk.RIGHT, fill=tk.Y); self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        try: default_font = tkfont.nametofont("TkDefaultFont"); self.bold_font = default_font.copy(); self.bold_font.configure(weight="bold")
        except tk.TclError: self.bold_font = None
        self.tree.tag_configure("Fatal", foreground="#FF5252", font=self.bold_font); self.tree.tag_configure("Error", foreground="#FF8A80"); self.tree.tag_configure("Warning", foreground="#FFD180"); self.tree.tag_configure("Info", foreground="#80CBC4"); self.tree.tag_configure("Connection", foreground="#FF8A80"); self.tree.tag_configure("Hardware", foreground="#FF8A80")
        self.tree.tag_configure("E-Stop", foreground="#FF5252", font=self.bold_font); self.tree.tag_configure("HVPS", foreground="#FF8A80"); self.tree.tag_configure("BagJam", foreground="#FFD180"); self.tree.tag_configure("License", foreground="#FFD180"); self.tree.tag_configure("Startup", foreground="#FF8A80")
        self.status_label = ttk.Label(self.status_bar, text="Bereit."); self.status_label.pack(side=tk.LEFT, padx=5)

    def _show_help_window(self):
        # (Unverändert)
        help_win = tk.Toplevel(self); help_win.title("Anleitung - MV3D System Analyzer"); help_win.geometry("800x600"); help_win.transient(self); help_win.grab_set(); text_area = scrolledtext.ScrolledText(help_win, wrap=tk.WORD, font=("Helvetica", 10), padx=10, pady=10); text_area.pack(expand=True, fill=tk.BOTH); text_area.insert(tk.INSERT, MV3D_HELP_TEXT); text_area.config(state="disabled")

    def _start_analysis_from_dialog(self):
        # (Angepasst - setzt Daten zurück)
        dir_path = filedialog.askdirectory(title="Wählen Sie den MV3D Log-Ordner")
        if not dir_path: return
        self.raw_df = pd.DataFrame(); self.incidents_df = pd.DataFrame(); self.filtered_incidents_df = pd.DataFrame(); self._update_treeview(self.filtered_incidents_df); self._populate_filters(); self.status_label.config(text="Starte Analyse...")
        self._create_loading_window("Initialisiere...")
        filter_enabled = self.filter_var.get()
        thread = threading.Thread(target=self._run_analysis_thread_safe, args=(dir_path, filter_enabled), daemon=True); thread.start()

    def _run_analysis_thread_safe(self, dir_path, filter_relatively):
        # (Unverändert)
        try: self._run_analysis_thread(dir_path, filter_relatively)
        except Exception as e: print(f"FATALER FEHLER im MV3D Analyse-Thread:\n{traceback.format_exc()}", file=sys.stderr); self.after(0, self._finalize_analysis, False, f"Schwerer Fehler: {e}")

    def _run_analysis_thread(self, dir_path, filter_relatively=False):
        # (Angepasst - Erweiterte Ausschlüsse + Pfad-Normalisierung)
        def progress_callback(progress, message):
             if self.loading_win: self.after(0, self._update_progress, progress, message)
        progress_callback(0, "Durchsuche Verzeichnis...")
        potential_files = [];
        names_to_exclude = ['abyss', 'anaconda', 'baddet', 'detpos', 'filtetdet', 'monitor_replication', 'btmp', 'cron', 'dmesg', 'dracut', 'lastlog', 'maillog', 'messages', 'secure', 'spooler', 'tallylog', 'wtmp', 'xorg', 'audit', 'history', 'prelink']
        files_to_exclude_general = ['config.xml', 'settings.ini', 'calib', 'report', 'yum.log', 'boot.log', 'nvidia-installer.log', 'spice-vdagent.log', 'app.log', 'bag.log', 'bhs.log', 'bms.log', 'fsm.log', 'fsm_bagdisp.log', 'fsm_bagid.log', 'fsm_ethip.log', 'fsm_plclog.log', 'optinet.log', 'plc.log', 'ups_monitor.log']
        filename_date_pattern = re.compile(r'(\d{4}-\d{2}-\d{2})'); latest_log_date = None
        for root, _, files in os.walk(dir_path):
            for file in files:
                filename = os.path.basename(file); filename_lower = filename.lower(); base_name, ext = os.path.splitext(filename_lower)
                full_path_orig = os.path.join(root, file); full_path = os.path.normpath(full_path_orig)
                if filename_lower in files_to_exclude_general or base_name in names_to_exclude: continue
                if filename_lower.startswith(('anaconda.', 'sa', 'sar', 'rpm_baseline')): continue
                if filename_lower.endswith(('.img', 'svr.log')) or ('verbose' in filename_lower and ext == '.csv'): continue
                if not (ext in ['.log', '.txt', ''] or re.search(r'-\d{8}$', base_name) or 'current' in filename_lower): continue # 'current' HINZUGEFÜGT
                file_date = None; date_match = filename_date_pattern.search(filename)
                if date_match:
                    try: file_date = datetime.strptime(date_match.group(1), '%Y-%m-%d').date(); latest_log_date = max(latest_log_date, file_date) if latest_log_date else file_date
                    except ValueError: pass
                potential_files.append((full_path, file_date))
        if not potential_files: self.after(0, self._finalize_analysis, False, "Keine relevanten MV3D Logs gefunden."); return
        original_log_files = []; msg_suffix = "."
        if filter_relatively and latest_log_date:
            date_limit = latest_log_date - timedelta(days=2); msg_suffix = f" (letzte 2 Tage relativ zu {latest_log_date.strftime('%Y-%m-%d')})."; progress_callback(10, f"Filtere Dateien bis {date_limit.strftime('%Y-%m-%d')}..."); files_kept_count = 0
            for file_path, file_date in potential_files:
                if file_date is None or file_date >= date_limit: original_log_files.append(file_path); files_kept_count += 1
            print(f"MV3D Datumsfilter: {files_kept_count} von {len(potential_files)} behalten.");
            if not original_log_files: self.after(0, self._finalize_analysis, False, f"Keine Logs im Datumsfenster gefunden{msg_suffix}."); return
        elif filter_relatively: print("WARNUNG: MV3D Relativer Filter aktiv, aber keine Daten gefunden. Analysiere alle."); original_log_files = [f[0] for f in potential_files]; msg_suffix = " (keine Datumsangaben gefunden)."
        else: original_log_files = [f[0] for f in potential_files]
        copied_log_files = []
        try:
            analysis_start_time_str = datetime.now().strftime("%Y-%m-%d_%H%M%S"); base_log_dir = os.path.join(os.getcwd(), "logs", "mv3d_system_analysis"); dest_dir = os.path.join(base_log_dir, f"analysis_{analysis_start_time_str}")
            if os.path.exists(dest_dir): shutil.rmtree(dest_dir); os.makedirs(dest_dir, exist_ok=True); print(f"Kopiere {len(original_log_files)} MV3D Logs nach: {dest_dir}")
            base_progress = 10; progress_callback(base_progress, "Kopiere Logs...")
            total_files_to_copy = len(original_log_files)
            for i, src_path in enumerate(original_log_files):
                if not os.path.exists(src_path): print(f"WARNUNG: Quelldatei existiert nicht: {src_path}", file=sys.stderr); continue
                try: dest_path = os.path.join(dest_dir, os.path.basename(src_path)); shutil.copy2(src_path, dest_path); copied_log_files.append(dest_path); progress = base_progress + int(((i + 1) / total_files_to_copy) * 40); progress_callback(progress, f"Kopiere: {os.path.basename(src_path)}")
                except Exception as copy_err: print(f"WARNUNG: Kopieren fehlgeschlagen {src_path}: {copy_err}", file=sys.stderr)
            if not copied_log_files: self.after(0, self._finalize_analysis, False, "Keine Dateien kopiert."); return
            progress_callback(50, f"{len(copied_log_files)} Dateien kopiert. Starte Analyse...")
        except Exception as e: print(f"FEHLER Ordner/Kopieren:\n{traceback.format_exc()}", file=sys.stderr); self.after(0, self._finalize_analysis, False, f"Fehler Kopieren: {e}"); return
        all_entries = []; total_files_to_analyze = len(copied_log_files); processed_files_count = 0; total_skipped_lines = 0; num_processes = max(1, multiprocessing.cpu_count() - 1); print(f"Starte MV3D Analyse mit {num_processes} Prozessen...")
        try:
             ctx = multiprocessing.get_context('spawn')
             with ctx.Pool(processes=num_processes) as pool:
                 results_iterator = pool.imap_unordered(_process_log_file_mv3d, copied_log_files)
                 for filename, file_entries, skipped_count in results_iterator:
                     if file_entries: all_entries.extend(file_entries)
                     total_skipped_lines += skipped_count; processed_files_count += 1; progress = 50 + int((processed_files_count / total_files_to_analyze) * 50); progress_callback(progress, f"Analysiere: {filename} ({processed_files_count}/{total_files_to_analyze})")
             print("MV3D Multiprocessing Pool beendet.")
        except Exception as pool_err: print(f"FEHLER MV3D Multiprocessing:\n{traceback.format_exc()}", file=sys.stderr); self.after(0, self._finalize_analysis, False, f"Pool Fehler: {pool_err}"); return
        if total_skipped_lines > 0: print(f"WARNUNG: {total_skipped_lines} MV3D Zeilen übersprungen (Zeitstempel).")
        if not all_entries: msg = "Keine relevanten MV3D Ereignisse gefunden."; msg += f" ({total_skipped_lines} Zeilen übersprungen)" if total_skipped_lines > 0 else ""; self.after(0, self._finalize_analysis, False, msg); return
        progress_callback(100, "Erstelle DataFrame...")
        self.raw_df = pd.DataFrame(all_entries); self.raw_df['Timestamp'] = pd.to_datetime(self.raw_df['Timestamp'], errors='coerce'); self.raw_df.dropna(subset=['Timestamp'], inplace=True)
        if self.raw_df.empty: self.after(0, self._finalize_analysis, False, "Keine gültigen Zeitstempel gefunden."); return
        self.raw_df.sort_values(by="Timestamp", inplace=True); self.raw_df.reset_index(drop=True, inplace=True); self.incidents_df = self.raw_df.copy(); self.incidents_df.reset_index(drop=True, inplace=True); self.filtered_incidents_df = self.incidents_df.copy()
        final_msg = f"{len(self.incidents_df)} MV3D Ereignisse gefunden{msg_suffix}"; final_msg += f" ({total_skipped_lines} Zeilen übersprungen)" if total_skipped_lines > 0 else ""; self.after(0, self._finalize_analysis, True, final_msg)

    def _finalize_analysis(self, success, message):
        if self.loading_win: self.loading_win.destroy(); self.loading_win = None
        if not success: messagebox.showwarning("Analyse fehlgeschlagen", message, parent=self.parent); self.raw_df=pd.DataFrame(); self.incidents_df=pd.DataFrame(); self.filtered_incidents_df=pd.DataFrame(); self._update_treeview(pd.DataFrame()); self._populate_filters(); return
        self.filtered_incidents_df = self.incidents_df.copy(); self._populate_filters(); self._apply_filters(); self.status_label.config(text=message); simple_message = message.split("(")[0].strip(); messagebox.showinfo("Analyse abgeschlossen", simple_message, parent=self.parent)

    def _populate_filters(self):
        self.severity_filter_combo.set('Alle'); self.date_filter_combo.set_date(None); self.source_filter_combo.set('Alle')
        self.source_filter_combo['values'] = ['Alle']; self.date_filter_combo.config(state='disabled')
        base_df = self.incidents_df;
        if base_df.empty: return
        if 'SourceFile' in base_df.columns: unique_sources = sorted(base_df['SourceFile'].unique());
        if unique_sources: self.source_filter_combo['values'] = ['Alle'] + unique_sources
        if 'Timestamp' in base_df.columns:
            valid_dates = base_df['Timestamp'].dropna();
            if not valid_dates.empty:
                min_date = valid_dates.min().date(); max_date = valid_dates.max().date()
                try: self.date_filter_combo.config(mindate=min_date, maxdate=max_date, state='readonly')
                except tk.TclError: self.date_filter_combo.config(state='readonly')

    def _apply_filters(self, event=None):
        # (Angepasst - mit allen Filtern)
        if self.incidents_df.empty: self._update_treeview(pd.DataFrame()); self.status_label.config(text="Keine Daten."); return
        df_to_filter = self.incidents_df.copy()
        selected_severity=self.severity_filter_combo.get(); selected_source=self.source_filter_combo.get()
        try: selected_date = self.date_filter_combo.get_date()
        except tk.TclError: selected_date = None
        if selected_severity and selected_severity != 'Alle': df_to_filter = df_to_filter[df_to_filter['Severity'] == selected_severity]
        if selected_source and selected_source != 'Alle': df_to_filter = df_to_filter[df_to_filter['SourceFile'] == selected_source]
        if selected_date: df_to_filter = df_to_filter[df_to_filter['Timestamp'].dt.date == selected_date]
        search_term = self.search_entry.get()
        if search_term:
            try: df_to_filter = df_to_filter[df_to_filter['OriginalLog'].str.contains(search_term, case=False, regex=True, na=False)]
            except re.error: messagebox.showwarning("Ungültige Suche", "Ungültige Regex.", parent=self.parent)
        errorcode_term = self.errorcode_entry.get()
        if errorcode_term:
            try: df_to_filter = df_to_filter[df_to_filter['OriginalLog'].str.contains(errorcode_term, case=False, regex=True, na=False)]
            except re.error: messagebox.showwarning("Ungültiger Fehlercode", "Ungültige Regex.", parent=self.parent)
        if self.estop_var.get(): df_to_filter = df_to_filter[df_to_filter['Severity'] == 'E-Stop']
        if self.hvps_var.get(): df_to_filter = df_to_filter[df_to_filter['Severity'] == 'HVPS']
        if self.bagjam_var.get(): df_to_filter = df_to_filter[df_to_filter['Severity'] == 'BagJam']
        if self.license_var.get(): df_to_filter = df_to_filter[df_to_filter['Severity'] == 'License']
        self.filtered_incidents_df = df_to_filter; self._update_treeview(self.filtered_incidents_df)
        self.status_label.config(text=f"{len(self.filtered_incidents_df)} Ereignisse nach Filterung.")

    def _reset_all_filters(self):
        # (Setzt ALLE Filter zurück)
        self.severity_filter_combo.set('Alle'); self.source_filter_combo.set('Alle'); self.date_filter_combo.set_date(None)
        self.search_entry.delete(0, tk.END); self.errorcode_entry.delete(0, tk.END)
        self.estop_var.set(False); self.hvps_var.set(False); self.bagjam_var.set(False); self.license_var.set(False)
        self._apply_filters()

    def _update_treeview(self, df_to_show):
        # (Unverändert)
        for i in self.tree.get_children(): self.tree.delete(i)
        if df_to_show is None or df_to_show.empty: return
        for index, row in df_to_show.iterrows():
            tag = row['Severity'] if pd.notna(row['Severity']) else ''; configured_tags = self.tree.tag_names(); final_tag = tag if tag in configured_tags else ''
            self.tree.insert("", "end", iid=index, tags=(final_tag,), values=( row['Timestamp'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['Timestamp']) else 'N/A', row['Severity'], row['SourceFile'], row['Event'] ))

    def _on_item_select(self, event):
        # (Unverändert)
        selected_item_iid = self.tree.focus();
        if not selected_item_iid: return
        try:
            iid_int = int(selected_item_iid)
            if iid_int in self.filtered_incidents_df.index:
                selected_display_row = self.filtered_incidents_df.loc[iid_int]
                timestamp_match = selected_display_row['Timestamp']; original_log_match = selected_display_row['OriginalLog']; source_file_match = selected_display_row['SourceFile']
                potential_matches = self.raw_df[ (self.raw_df['Timestamp'] == timestamp_match) & (self.raw_df['OriginalLog'] == original_log_match) & (self.raw_df['SourceFile'] == source_file_match) ]
                if not potential_matches.empty: selected_raw_row = self.raw_df.loc[potential_matches.index[0]]; MV3DCasefileWindow(self.parent, selected_raw_row, self.raw_df)
                else: messagebox.showwarning("Fehler", "Rohdaten-Eintrag nicht gefunden.", parent=self.parent)
            else: print(f"WARNUNG: Index {iid_int} nicht in filtered_incidents_df gefunden."); messagebox.showwarning("Fehler", "Ausgewählter Eintrag nicht gefunden (Indexproblem).", parent=self.parent)
        except (ValueError, KeyError, AttributeError, IndexError) as e: print(f"Fehler Öffnen Detailfenster (IID: {selected_item_iid}): {e}\n{traceback.format_exc()}"); messagebox.showwarning("Fehler", "Detailansicht nicht möglich.", parent=self.parent)

    def _create_loading_window(self, initial_message="Initialisiere..."):
        # (Unverändert)
        if self.loading_win and self.loading_win.winfo_exists(): self.loading_win.destroy()
        self.loading_win = tk.Toplevel(self.parent); self.loading_win.title("Ladevorgang"); self.loading_win.geometry("450x130"); self.loading_win.resizable(False, False); self.parent.update_idletasks(); x=self.parent.winfo_screenwidth()//2-self.loading_win.winfo_width()//2; y=self.parent.winfo_screenheight()//2-self.loading_win.winfo_height()//2; self.loading_win.geometry(f"+{x}+{y}"); self.loading_win.transient(self.parent); self.loading_win.grab_set(); self.loading_label = ttk.Label(self.loading_win, text=initial_message, font=("Helvetica", 10)); self.loading_label.pack(pady=(15, 5), padx=10, anchor="w"); self.loading_progress_bar = ttk.Progressbar(self.loading_win, orient="horizontal", mode="determinate"); self.loading_progress_bar.pack(fill=tk.X, expand=True, padx=10); self.percent_label = ttk.Label(self.loading_win, text="0%", font=("Helvetica", 10)); self.percent_label.pack(pady=5)

    def _update_progress(self, progress, message):
        # (Unverändert)
        if self.loading_win and self.loading_win.winfo_exists():
             try: self.loading_win.lift(); self.loading_label.config(text=f"{message}"); self.loading_progress_bar['value'] = progress; self.percent_label.config(text=f"{progress}%"); self.loading_win.update_idletasks()
             except tk.TclError: pass


# --- Main execution block ---
if __name__ == "__main__":
    multiprocessing.freeze_support()
    print(f"--- Running __main__ block in mv3d_system_analyzer_app.py (PID: {os.getpid()}) ---")
    root = tk.Tk()
    app = MV3DSystemAnalyzerApp(root)
    root.mainloop()
    print(f"--- Exiting __main__ block in mv3d_system_analyzer_app.py (PID: {os.getpid()}) ---")