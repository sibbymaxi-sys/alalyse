# mv3d_casefile_window.py
# (Updated: Keyword Highlighting in Context)
import tkinter as tk
from tkinter import ttk, scrolledtext
import pandas as pd
from datetime import timedelta
import re
import os
import sys

# (Sicherheits-Import-Fix)
file_dir = os.path.dirname(os.path.abspath(__file__))
if file_dir not in sys.path:
    sys.path.insert(0, file_dir)

try:
    from mv3d_error_definitions import ERROR_DEFINITIONS, LOG_CONTEXT_RULES
except ImportError:
    ERROR_DEFINITIONS = {}
    LOG_CONTEXT_RULES = [] # Bleibt leer, wenn Import fehlschlägt


class MV3DCasefileWindow(tk.Toplevel):
    def __init__(self, parent, selected_row, raw_df):
        super().__init__(parent)
        self.title("MV3D System-Analyse: Fall-Details")
        self.geometry("1000x700")
        self.transient(parent)
        self.grab_set()

        self.selected_row = selected_row
        self.raw_df = raw_df
        self.error_details = self._analyze_error(selected_row['OriginalLog'])

        self._setup_ui()
        self._populate_data()

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Top Frame: Error Details (unverändert) ---
        top_frame = ttk.LabelFrame(main_frame, text="Fehler-Analyse (MV3D)", padding=10)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(top_frame, text="Meldung:", font=("-weight bold")).grid(row=0, column=0, sticky="nw", padx=5, pady=2)
        self.error_msg_label = ttk.Label(top_frame, text="...", wraplength=850, font=("Courier New", 10))
        self.error_msg_label.grid(row=0, column=1, sticky="nw", padx=5, pady=2)
        ttk.Label(top_frame, text="Mögliche Ursache:", font=("-weight bold")).grid(row=1, column=0, sticky="nw", padx=5, pady=2)
        self.error_cause_label = ttk.Label(top_frame, text="...", wraplength=850)
        self.error_cause_label.grid(row=1, column=1, sticky="nw", padx=5, pady=2)
        ttk.Label(top_frame, text="Empfehlung:", font=("-weight bold")).grid(row=2, column=0, sticky="nw", padx=5, pady=2)
        self.error_action_label = ttk.Label(top_frame, text="...", wraplength=850)
        self.error_action_label.grid(row=2, column=1, sticky="nw", padx=5, pady=2)
        top_frame.columnconfigure(1, weight=1)

        # --- Bottom Frame: Log Context ---
        bottom_frame = ttk.LabelFrame(main_frame, text="Log-Kontext (Umgebung der Meldung)", padding=10)
        bottom_frame.pack(fill=tk.BOTH, expand=True, pady=(5,0))

        text_area_frame = ttk.Frame(bottom_frame)
        text_area_frame.pack(fill=tk.BOTH, expand=True)

        hsb = ttk.Scrollbar(text_area_frame, orient="horizontal")
        vsb = ttk.Scrollbar(text_area_frame, orient="vertical")

        self.log_text_area = tk.Text(text_area_frame, wrap=tk.NONE,
                                        font=("Courier New", 9), height=10,
                                        yscrollcommand=vsb.set,
                                        xscrollcommand=hsb.set)

        vsb.config(command=self.log_text_area.yview)
        hsb.config(command=self.log_text_area.xview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.log_text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Standard Tags
        self.log_text_area.tag_configure("highlight_error", background="#5B0000", foreground="white")
        # self.log_text_area.tag_configure("highlight_context", background="#3E3E3E") # Veraltet, ersetzt durch Keyword
        # NEU: Tag für Keywords
        self.log_text_area.tag_configure("highlight_keyword", background="#6A4D00", foreground="white") # Dunkelorange/Gelb

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(button_frame, text="Log-Kontext kopieren", command=self._copy_log_context).pack(side=tk.RIGHT)

    def _copy_log_context(self):
        # (Unverändert)
        try:
            original_state = self.log_text_area.cget("state")
            self.log_text_area.config(state=tk.NORMAL)
            content = self.log_text_area.get(1.0, tk.END)
            self.clipboard_clear()
            self.clipboard_append(content)
            self.log_text_area.config(state=original_state)
        except Exception as e:
            messagebox.showerror("Kopierfehler", f"Konnte den Text nicht kopieren:\n{e}", parent=self)

    def _analyze_error(self, error_line):
        # (Unverändert)
        for pattern, details in ERROR_DEFINITIONS.items():
            if re.search(pattern, error_line, re.IGNORECASE):
                try:
                    matches = re.search(pattern, error_line, re.IGNORECASE).groups()
                    return {
                        "cause": details['cause'].format(*matches),
                        "action": details['action'].format(*matches)
                    }
                except Exception:
                     return details
        return {
            "cause": "Keine spezifische Ursache in der MV3D-Wissensdatenbank gefunden.",
            "action": "Überprüfen Sie den Log-Kontext auf zusammenhängende Fehler."
        }

    # --- START: Überarbeitete _populate_data ---
    def _populate_data(self):
        """Füllt die UI-Elemente und hebt Keywords im Kontext hervor."""

        self.error_msg_label.config(text=self.selected_row['OriginalLog'])
        self.error_cause_label.config(text=self.error_details['cause'])
        self.error_action_label.config(text=self.error_details['action'])

        try:
            if not hasattr(self.selected_row, 'name'):
                 self.log_text_area.config(state=tk.NORMAL)
                 self.log_text_area.insert(tk.END, "Fehler: Konnte Zeilenindex (name) nicht finden.")
                 self.log_text_area.config(state=tk.DISABLED)
                 return

            row_index = self.selected_row.name
            context_before = self.raw_df.loc[max(0, row_index - 20) : row_index - 1]
            context_after = self.raw_df.loc[row_index + 1 : min(len(self.raw_df) - 1, row_index + 20)]

            self.log_text_area.config(state=tk.NORMAL)
            self.log_text_area.delete(1.0, tk.END)

            # Funktion zum Einfügen und Hervorheben
            def insert_and_highlight(row_data, base_tag=None):
                line_text = self._format_log_line(row_data) + "\n"
                start_index = self.log_text_area.index(tk.END + "-1c") # Start der neuen Zeile
                self.log_text_area.insert(tk.END, line_text, base_tag)
                end_index = self.log_text_area.index(tk.END + "-1c") # Ende der neuen Zeile

                # Wende Keyword-Hervorhebung an
                original_log = str(row_data.get('OriginalLog', ''))
                for rule in LOG_CONTEXT_RULES:
                    try:
                        # Finde alle Vorkommen des Keywords in der Originalzeile
                        for match in re.finditer(rule, original_log, re.IGNORECASE):
                            # Finde die Position des Matches im formatierten Text
                            # (Wir suchen ab dem Zeilenstart im Text Area)
                            match_start = match.start()
                            match_end = match.end()

                            # Suche das gematchte Wort im formatierten Text der aktuellen Zeile
                            # Dies ist nötig, da _format_log_line Präfixe hinzufügt
                            # Wir suchen das Wort case-insensitive im formatierten String
                            search_pattern = re.escape(match.group(0)) # Exaktes gematchtes Wort
                            count_var = tk.IntVar()
                            found_pos = self.log_text_area.search(search_pattern, start_index, stopindex=end_index, count=count_var, nocase=True)

                            if found_pos:
                                # Berechne Start- und End-Index im Text Area für das gefundene Wort
                                highlight_start = found_pos
                                highlight_end = f"{found_pos}+{count_var.get()}c"
                                self.log_text_area.tag_add("highlight_keyword", highlight_start, highlight_end)

                    except re.error as e:
                        print(f"WARNUNG: Ungültiges Regex '{rule}' in LOG_CONTEXT_RULES: {e}")
                    except tk.TclError as e: # Fehler beim Suchen/Taggen abfangen
                        print(f"Fehler beim Hervorheben für Regel '{rule}': {e}")


            # Zeilen davor einfügen und hervorheben
            for _, row in context_before.iterrows():
                insert_and_highlight(row)

            # Die Fehlerzeile einfügen (mit Fehler-Tag) und hervorheben
            insert_and_highlight(self.selected_row, base_tag="highlight_error")

            # Zeilen danach einfügen und hervorheben
            for _, row in context_after.iterrows():
                insert_and_highlight(row)

            self.log_text_area.config(state=tk.DISABLED)

        except Exception as e:
            try:
                original_state = self.log_text_area.cget("state")
                self.log_text_area.config(state=tk.NORMAL)
                self.log_text_area.delete(1.0, tk.END) # Vorherigen Inhalt löschen
                self.log_text_area.insert(tk.END, f"Fehler beim Laden des Log-Kontexts: {e}\n{traceback.format_exc()}") # Mehr Details
                self.log_text_area.config(state=original_state)
            except tk.TclError:
                print(f"Fehler beim Anzeigen der Log-Kontext-Fehlermeldung: {e}")
    # --- ENDE: Überarbeitete _populate_data ---


    def _format_log_line(self, row):
        # (Unverändert)
        ts = row['Timestamp']
        if pd.isna(ts):
            ts_str = " " * 19
        else:
            ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')

        source_file = row.get('SourceFile', 'UNKNOWN')
        source_file_display = f"{source_file[:18]:<18}" if len(source_file) > 18 else f"{source_file:<18}"
        log_content = str(row.get('OriginalLog', ''))
        return f"[{ts_str}] [{source_file_display}] {log_content}"

    def _get_context_tag(self, row):
        # Diese Funktion wird nicht mehr direkt für die Hervorhebung verwendet,
        # da die Logik in _populate_data verschoben wurde.
        # Sie kann entfernt oder beibehalten werden, falls sie woanders benötigt wird.
        return "normal" # Gibt einfach "normal" zurück