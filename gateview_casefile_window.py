# gateview_casefile_window.py
import tkinter as tk
from tkinter import ttk, scrolledtext, font as tkfont
import pandas as pd
from datetime import timedelta
import re
import traceback # Import traceback

try:
    # Importiert die Master-Funktion, die den Klartext zurückgibt
    from cs_error_definitions import get_system_error_details
except ImportError:
    print("WARNUNG (Casefile): cs_error_definitions.py nicht gefunden.")
    # Fallback gibt Kategorie und Originalzeile zurück
    def get_system_error_details(filename, log_line): return "Unknown", log_line

class GateViewCasefileWindow:
    def __init__(self, parent, selected_row, raw_df):
        self.parent = parent
        # Store both the selected series and the full raw DataFrame
        self.selected_row_series = selected_row # Keep the Series
        self.raw_df = raw_df

        self.win = tk.Toplevel(parent)
        self.win.title("Casefile Detailansicht")
        self.win.geometry("1000x750")
        self.win.transient(parent)
        self.win.grab_set()

        # Safely get data from the selected row (Series)
        timestamp = pd.to_datetime(self.selected_row_series.get('Timestamp', pd.NaT))
        source_file = self.selected_row_series.get('SourceFile', 'N/A')
        original_log = self.selected_row_series.get('OriginalLog', '') # Get original log

        time_window_seconds = 30 # Context window

        if pd.isna(timestamp):
            timestamp_str = "Ungültiger Zeitstempel"
            time_window_start, time_window_end = None, None
        else:
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            time_window_start = timestamp - timedelta(seconds=time_window_seconds)
            time_window_end = timestamp + timedelta(seconds=time_window_seconds)

        # --- Analyze error to get Klartext ---
        # error_category holds 'Fatal', 'Error', etc.
        # error_klartext holds the human-readable message from definitions or a fallback
        self.error_category, self.error_klartext, self.is_fallback = self._analyze_error(source_file, original_log)

        # --- Setup UI ---
        main_frame = ttk.Frame(self.win, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        info_frame = ttk.LabelFrame(main_frame, text="Ereignisdetails", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(info_frame, text="Zeitstempel:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(info_frame, text=timestamp_str).grid(row=0, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(info_frame, text="Quelldatei:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(info_frame, text=source_file).grid(row=1, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(info_frame, text="Kategorie:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(info_frame, text=self.error_category).grid(row=2, column=1, sticky="w", padx=5, pady=2)

        # --- Display Klartext ---
        ttk.Label(info_frame, text="Klartext:").grid(row=3, column=0, sticky="nw", padx=5, pady=2)
        # Add hint if it's a fallback message
        display_message = self.error_klartext
        if self.is_fallback:
            display_message += " (Hinweis: Keine spezifische Definition gefunden)"
        msg_label = ttk.Label(info_frame, text=display_message, wraplength=850, justify=tk.LEFT)
        msg_label.grid(row=3, column=1, sticky="w", padx=5, pady=2)
        # --- End Display Klartext ---

        context_frame = ttk.LabelFrame(main_frame, text=f"Log-Kontext (±{time_window_seconds} Sekunden)", padding=10)
        context_frame.pack(fill=tk.BOTH, expand=True)

        self.context_text = scrolledtext.ScrolledText(context_frame, wrap=tk.WORD, font=("Courier New", 9), height=20)
        self.context_text.pack(fill=tk.BOTH, expand=True)

        # Font and Tag Configuration (remains the same as previous)
        self.keywords_to_highlight = {
             "fatal": "fatal_kw", "critical": "fatal_kw", "error": "error_kw", "fail": "error_kw", "fault": "error_kw",
             "warning": "warning_kw", "warn": "warning_kw", "timeout": "warning_kw", "refused": "error_kw", "denied": "error_kw",
             "exception": "error_kw", "traceback": "error_kw", "jam": "warning_kw", "block": "warning_kw",
             "estop": "fatal_kw", "ilock": "fatal_kw", "interlock": "fatal_kw", "down": "fatal_kw", "stop": "fatal_kw",
             "restart": "restart_kw" }
        try:
            default_font_tuple = ("Courier New", 9); self.context_text.config(font=default_font_tuple)
            bold_font = tkfont.Font(family=default_font_tuple[0], size=default_font_tuple[1], weight="bold")
            self.context_text.tag_configure("highlight_line", background="#555555", foreground="white", font=bold_font)
            self.context_text.tag_configure("fatal_kw", foreground="#FF5252", font=bold_font, underline=True)
            self.context_text.tag_configure("error_kw", foreground="#FF8A80", underline=True)
            self.context_text.tag_configure("warning_kw", foreground="#FFD180", underline=True)
            self.context_text.tag_configure("restart_kw", foreground="#8C9EFF", underline=True)
            self.context_text.tag_configure("line_fatal", foreground="#FF5252", font=bold_font)
            self.context_text.tag_configure("line_error", foreground="#FF8A80")
            self.context_text.tag_configure("line_warning", foreground="#FFD180")
        except tk.TclError as e: # Fallback tags
            print(f"WARNUNG (Casefile Font): {e}")
            self.context_text.tag_configure("highlight_line", background="#555555", foreground="white")
            # ... (other fallback tags) ...

        self._load_context(timestamp, time_window_start, time_window_end, original_log)

        button_frame = ttk.Frame(main_frame); button_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(button_frame, text="Schließen", command=self.win.destroy).pack(side=tk.RIGHT)

    def _analyze_error(self, filename, error_line):
        """
        Versucht, detaillierte Fehlerinfos (Klartext) zu erhalten.
        Gibt zurück: (Kategorie, Klartext-Nachricht, is_fallback_bool).
        """
        if not error_line:
            return "Info", "Keine Log-Zeile ausgewählt.", False

        # 1. Versuche, spezifische Definition zu finden
        category, klartext = get_system_error_details(filename, error_line)
        if category:
            # Erfolg! Wir haben eine Definition gefunden.
            return category, klartext, False # False = kein Fallback

        # 2. Fallback: Versuche, aus der 'Event'-Spalte zu parsen (aus system_analyzer)
        # Die 'Event'-Spalte sollte schon die bereinigte Meldung enthalten
        event_col_value = self.selected_row_series.get('Event', '')
        match = re.match(r'\[(.*?)\](.*)', event_col_value)
        if match:
            fallback_category = match.group(1).strip()
            fallback_message = match.group(2).strip()
            # Bereinige die Fallback-Nachricht ggf. weiter
            fallback_message = fallback_message.replace("(FC", " (FC") # Korrigiere Leerzeichen
            return fallback_category, fallback_message, True # True = ist Fallback

        # 3. Absoluter Fallback: Benutze die Originalzeile (falls 'Event' leer war)
        # Versuche zumindest, den Zeitstempel und ggf. Log-Level zu entfernen
        fallback_message = error_line
        # Verwende den Timestamp-Parser, um den Anfang der Nachricht zu finden
        try:
            # Brauchen Jahr für Parser
            year_str = str(self.selected_row_series.get('Timestamp', pd.NaT).year) if pd.notna(self.selected_row_series.get('Timestamp', pd.NaT)) else str(datetime.now().year)
            _, msg_start = _parse_timestamp_static(error_line, year_str)
            if msg_start is not None and msg_start < len(error_line):
                fallback_message = fallback_message[msg_start:].strip()
        except Exception:
            pass # Behalte Originalzeile, wenn Timestamp-Parsing fehlschlägt

        # Entferne bekannte Präfixe
        fallback_message = re.sub(r'^(?:ERROR|WARNING|INFO|DEBUG|FATAL|CRITICAL)\s*[:\-]\s*', '', fallback_message, flags=re.IGNORECASE)
        fallback_message = re.sub(r'^\[.*?\]\s*:\s*', '', fallback_message) # Z.B. [scs:123]

        return "Unknown", fallback_message.strip(), True # True = ist Fallback


    def _apply_keyword_highlighting(self, line_content, start_index):
        """Findet Schlüsselwörter und wendet Tags an."""
        line_lower = line_content.lower()
        for keyword, tag in self.keywords_to_highlight.items():
            start = 0
            while True:
                pos = line_lower.find(keyword, start)
                if pos == -1: break
                kw_start = f"{start_index}+{pos}c"
                kw_end = f"{start_index}+{pos + len(keyword)}c"
                # Prüfe, ob der Tag existiert, bevor er angewendet wird
                if tag in self.context_text.tag_names():
                    self.context_text.tag_add(tag, kw_start, kw_end)
                start = pos + len(keyword)

    def _load_context(self, selected_ts, start_time, end_time, selected_original_log):
        """Lädt Log-Zeilen und wendet Hervorhebungen an."""
        if start_time is None or end_time is None:
            self.context_text.insert(tk.END, "Zeitfenster konnte nicht bestimmt werden."); self.context_text.config(state=tk.DISABLED); return

        try:
            context_df = self.raw_df[
                (self.raw_df['Timestamp'] >= start_time) &
                (self.raw_df['Timestamp'] <= end_time)
            ].sort_values(by='Timestamp')

            if context_df.empty:
                self.context_text.insert(tk.END, "Keine weiteren Log-Einträge in diesem Zeitfenster gefunden.")
            else:
                for index, row in context_df.iterrows():
                    ts = row.get('Timestamp', pd.NaT)
                    ts_str = ts.strftime('%H:%M:%S.%f')[:-3] if pd.notna(ts) else "??:??:??.???"
                    log_line = row.get('OriginalLog', '')
                    source_file = row.get('SourceFile', 'N/A')
                    full_line_content = f"[{ts_str}][{source_file}] {log_line}\n"

                    start_index = self.context_text.index(tk.END + "-1c")
                    self.context_text.insert(tk.END, full_line_content)
                    end_index = self.context_text.index(tk.END + "-1c")

                    # Zeilen-Hervorhebung basierend auf Kategorie
                    line_category, _, _ = self._analyze_error(source_file, log_line)
                    line_tag = f"line_{line_category.lower()}" if line_category and line_category != "Unknown" else None
                    if line_tag and line_tag in self.context_text.tag_names():
                        self.context_text.tag_add(line_tag, start_index, end_index)

                    # Keyword-Hervorhebung
                    self._apply_keyword_highlighting(full_line_content, start_index)

                    # Markiere die ausgewählte Zeile
                    is_selected_line = (ts == selected_ts and log_line == selected_original_log)
                    if is_selected_line:
                         if "highlight_line" in self.context_text.tag_names():
                             self.context_text.tag_add("highlight_line", start_index, end_index)

        except Exception as e:
            self.context_text.insert(tk.END, f"Fehler beim Laden des Kontexts:\n{e}\n{traceback.format_exc()}")

        self.context_text.config(state=tk.DISABLED)

# (Example Usage __main__ block remains the same)
if __name__ == '__main__':
    # ...(rest of the __main__ block for testing)...
    dummy_data = { # Updated dummy data
        'Timestamp': [pd.Timestamp('2023-10-26 10:00:05.100'),
                      pd.Timestamp('2023-10-26 10:00:10.200'), # Selected Row
                      pd.Timestamp('2023-10-26 10:00:15.300'),
                      pd.Timestamp('2023-10-26 10:00:18.500')],
        'SourceFile': ['scs_log.log', 'scs_log.log', 'plc_log.csv', 'dbm.log'],
        'Event': ['[Info] System started', '[Fatal] Interlock-Fehler (FC5)', '[Error] PLC Alarm: Motorschutzschalter M1', '[Warning] DBM: Connection pool low.'], # Event column from analyzer
        'OriginalLog': ['Oct 26 10:00:05.100 INFO: System started normally',
                        'Oct 26 10:00:10.200 ERROR: Reported Error - 5 (STAT_VAL_SCS_MACHINE_FAULTCAUSE_ILOCK)',
                        '2023-10-26 10:00:15,300,ALARM,received alarm with id 10201',
                        '2023-10-26 10:00:18.500 [WARN] DBM: Connection pool low.']
    }
    dummy_raw_df = pd.DataFrame(dummy_data)
    if not dummy_raw_df.empty:
        # Use .loc[index] for robust selection if index is not default 0, 1, 2...
        # Assuming default index here for simplicity:
        dummy_selected_row_series = dummy_raw_df.iloc[1] # Pass the Series
        root = tk.Tk(); root.withdraw()
        # Pass the Series, not the index
        casefile_win = GateViewCasefileWindow(root, dummy_selected_row_series, dummy_raw_df)
        root.mainloop()
    else: print("Dummy data is empty, cannot run example.")