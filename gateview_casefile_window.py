# gateview_casefile_window.py
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import timedelta
import re
import pandas as pd

from clearscan_error_definitions import get_error_details

class GateViewCasefileWindow(tk.Toplevel):
    
    def __init__(self, master, selected_row, raw_df):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.title("Fall-Akte / Klartext-Analyse (ClearScan)")
        self.geometry("1100x700")

        self.full_df = raw_df
        self.selected_row = selected_row

        self._analyze_and_build()

    def _analyze_and_build(self):
        incident_time = self.selected_row['Timestamp']
        
        # Variable in beiden Fällen definieren, um UnboundLocalError zu vermeiden
        incident_df = pd.DataFrame() 

        if pd.notna(incident_time):
            start_time = incident_time - timedelta(seconds=15)
            end_time = incident_time + timedelta(seconds=15)
            
            # Sicherstellen, dass die Variable im if-Block einen Wert hat
            incident_df = self.full_df[
                (self.full_df['Timestamp'].notna()) & 
                (self.full_df['Timestamp'] >= start_time) & 
                (self.full_df['Timestamp'] <= end_time)
            ].copy()
        else:
            # Hier wird die Variable im else-Block zugewiesen
            incident_df = self.full_df.loc[[self.selected_row.name]].copy()

        print("Anzahl der Einträge im Zeitfenster:", len(incident_df))

        root_cause_text = "Kein spezifischer Fehler im Zeitfenster gefunden."
        root_cause_row = self.selected_row
        
        error_pattern = r"(?:ERROR|FAIL|FAULT|WARNING|Restarting Script)"
        error_mask = incident_df['OriginalLog'].str.contains(error_pattern, flags=re.IGNORECASE, na=False)
        specific_errors = incident_df[error_mask]
        
        if not specific_errors.empty:
            root_cause_row = specific_errors.iloc[0]
            root_cause_text = root_cause_row['OriginalLog'].strip()

        klartext_beschreibung, empfohlene_aktion = get_error_details(root_cause_text)

        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill="both", expand=True)

        header_frame = ttk.LabelFrame(main_frame, text="Vorfalls-Analyse", padding=10)
        header_frame.pack(fill="x", pady=5)
        ttk.Label(header_frame, text="Zeitpunkt:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Label(header_frame, text=incident_time.strftime('%Y-%m-%d %H:%M:%S') if pd.notna(incident_time) else "N/A (konnte nicht aus Log extrahiert werden)").grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(header_frame, text="Original-Meldung:", font=("Helvetica", 10, "bold")).grid(row=1, column=0, sticky="w", pady=2)
        ttk.Label(header_frame, text=root_cause_text, foreground="red", wraplength=800).grid(row=1, column=1, sticky="w", padx=5)
        ttk.Label(header_frame, text="Klartext-Analyse:", font=("Helvetica", 10, "bold")).grid(row=2, column=0, sticky="w", pady=2)
        ttk.Label(header_frame, text=klartext_beschreibung, wraplength=800).grid(row=2, column=1, sticky="w", padx=5)
        ttk.Label(header_frame, text="Empfohlene Aktion:", font=("Helvetica", 10, "bold")).grid(row=3, column=0, sticky="w", pady=2)
        ttk.Label(header_frame, text=empfohlene_aktion, wraplength=800).grid(row=3, column=1, sticky="w", padx=5)
        
        conversation_frame = ttk.LabelFrame(main_frame, text="Chronologische Ereignisse", padding=10)
        conversation_frame.pack(fill="both", expand=True, pady=10)
        log_text = scrolledtext.ScrolledText(conversation_frame, wrap="word", font=("Courier New", 9))
        log_text.pack(fill="both", expand=True)

        for _, row in incident_df.iterrows():
            timestamp_str = row['Timestamp'].strftime('%H:%M:%S.%f')[:-3] if pd.notna(row['Timestamp']) else 'N/A'
            line_to_insert = f"[{timestamp_str}] {row['OriginalLog']}\n"
            tags = []
            if row.name == root_cause_row.name:
                tags.append("root_cause")
            elif re.search(error_pattern, row['OriginalLog'], re.IGNORECASE):
                tags.append("error_word")
            log_text.insert(tk.END, line_to_insert, tuple(tags))

        # Korrigierte Farbcodes für bessere Lesbarkeit
        log_text.tag_configure("root_cause", background="#8B0000", foreground="white", font=("Courier New", 9, "bold"))
        log_text.tag_configure("error_word", foreground="#FFA500")
        log_text.config(state="disabled")