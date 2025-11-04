# mv3d_app.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import threading
import os
import sys
import traceback
import multiprocessing
from datetime import datetime

# Lokale Module importieren
from base_app import BaseApp
import config_manager as cfg

# --- START KORREKTUR ---
# Importiere die KORREKTE Funktion zum Parsen EINER Datei
try:
    from mv3d_log_parser import parse_mv3d_log
except ImportError as e:
    print(f"FEHLER: Konnte mv3d_log_parser Modul nicht importieren: {e}")
    sys.exit(1)
except AttributeError as e:
    # Dieser Fehler sollte jetzt nicht mehr auftreten
    print(f"FEHLER: Funktion 'parse_mv3d_log' nicht in mv3d_log_parser gefunden: {e}")
    sys.exit(1)
# --- ENDE KORREKTUR ---

from log_previewer import preview_log_directory
from help_texts import MV3D_HELP_TEXT
from ftp_dialog import FTPDialog
from ftp_client import SFTPClient
from sftp_log_window import SFTPLogWindow
from mv3d_system_analyzer_app import MV3DSystemAnalyzerApp


class MV3DApp(BaseApp):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, app_name="MV3D Analyzer", version="1.0", *args, **kwargs)

        self.raw_df = pd.DataFrame()
        self.loading_win = None
        self.current_directory = None

        # Mapping von Dateinamen zu Parser-Typen (wird für Preview UND Verarbeitung gebraucht)
        self.parser_map = {
            # Nur MV3D-spezifische Log-Dateien auflisten
            "bms.log": "mv3d",
            "dpp.log": "mv3d",
            "iac.log": "mv3d",
            "plc.log": "mv3d",
            "scs.log": "mv3d"
            # Füge hier weitere hinzu, falls nötig
        }

        self._setup_ui()

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=5)

        ttk.Button(top_frame, text="Log-Ordner öffnen...", command=self._load_directory_dialog).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(top_frame, text="System-Analyse (MV3D)", command=self._launch_mv3d_system_analyzer).pack(side=tk.LEFT, padx=15, pady=5)

        self.info_label = ttk.Label(top_frame, text="Kein Ordner geladen.")
        self.info_label.pack(side=tk.LEFT, padx=20, pady=5)

        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.tree = ttk.Treeview(tree_frame, columns=("Timestamp", "Source", "IATA", "Klartext", "OriginalLog"), show="headings")
        self.tree.heading("Timestamp", text="Zeitstempel")
        self.tree.column("Timestamp", width=160, anchor='w')
        self.tree.heading("Source", text="Quelle")
        self.tree.column("Source", width=80, anchor='center')
        self.tree.heading("IATA", text="IATA")
        self.tree.column("IATA", width=80, anchor='center')
        self.tree.heading("Klartext", text="Ereignis")
        self.tree.column("Klartext", width=500, anchor='w')
        self.tree.heading("OriginalLog", text="Original Log")
        self.tree.column("OriginalLog", width=500, anchor='w')

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.status_label = ttk.Label(self.status_bar, text="Bereit.")
        self.status_label.pack(side=tk.LEFT, padx=5)

    def _launch_mv3d_system_analyzer(self):
        new_window = tk.Toplevel(self)
        new_window.title("Eigenständige System-Analyse (MV3D)")
        new_window.geometry("1100x700")
        MV3DSystemAnalyzerApp(new_window)

    def _load_directory_dialog(self):
        config = cfg.load_config()
        last_dir = config.get("last_mv3d_dir", os.getcwd())
        dir_path = filedialog.askdirectory(title="Wählen Sie den MV3D Log-Ordner", initialdir=last_dir)

        if not dir_path:
            return

        self.current_directory = dir_path
        config["last_mv3d_dir"] = dir_path
        cfg.save_config(config)

        min_date, max_date, count = preview_log_directory(dir_path, self.parser_map)

        if min_date and max_date:
            date_str = f"{min_date.strftime('%d.%m.%Y %H:%M')} - {max_date.strftime('%d.%m.%Y %H:%M')}"
            info_text = f"Ordner: ...{os.path.basename(dir_path)} | Zeitbereich: {date_str} | Ca. {count:,} Einträge gefunden."
            self.info_label.config(text=info_text)

            confirm = messagebox.askyesno("Analyse starten?", f"{info_text}\n\nMöchten Sie diesen Ordner jetzt analysieren?", parent=self)
            if confirm:
                self._start_loading_process(dir_path)
        else:
            info_text = f"Ordner: ...{os.path.basename(dir_path)} | Keine Log-Dateien mit Zeitstempel gefunden."
            self.info_label.config(text=info_text)
            messagebox.showwarning("Keine Daten", "Keine bekannten Log-Dateien mit Zeitstempeln im ausgewählten Ordner gefunden.", parent=self)

    def _start_loading_process(self, dir_path):
        self._create_loading_window()
        self.raw_df = pd.DataFrame()
        thread = threading.Thread(target=self._load_and_process_directory, args=(dir_path,), daemon=True)
        thread.start()
        self.after(100, self._check_thread, thread)

    # --- START KORREKTUR (_load_and_process_directory) ---
    def _load_and_process_directory(self, dir_path):
        """Durchsucht das Verzeichnis und parst jede relevante Log-Datei einzeln."""
        all_dfs = []
        files_to_parse = []

        # Finde alle relevanten Dateien im Verzeichnis
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.lower() in self.parser_map: # Prüfe gegen unser Mapping
                    files_to_parse.append(os.path.join(root, file))

        if not files_to_parse:
            self.after(0, self._update_progress, 100, "Keine Log-Dateien gefunden")
            return # Frühzeitig beenden

        total_files = len(files_to_parse)
        for i, file_path in enumerate(files_to_parse):
            filename = os.path.basename(file_path)
            # Aktualisiere Fortschritt pro Datei
            progress = int(((i + 1) / total_files) * 100)
            self.after(0, self._update_progress, progress, f"Analysiere {filename}...")

            try:
                # Rufe den korrigierten Parser für EINE Datei auf
                df_single = parse_mv3d_log(file_path)
                if not df_single.empty:
                    all_dfs.append(df_single)
            except Exception as e:
                print(f"Fehler beim Parsen von {filename}: {e}")
                # Optional: Hier eine Meldung im UI anzeigen
                # self.after(0, messagebox.showerror, "Parse-Fehler", f"Fehler beim Lesen von {filename}:\n{e}")

        if all_dfs:
            # Kombiniere alle DataFrames und sortiere nach Zeitstempel
            self.raw_df = pd.concat(all_dfs, ignore_index=True)
            self.raw_df.sort_values(by="Timestamp", inplace=True)
            self.raw_df.reset_index(drop=True, inplace=True)
        else:
            # Stelle sicher, dass raw_df ein leerer DataFrame ist, wenn nichts gefunden wurde
            self.raw_df = pd.DataFrame()

        self.after(0, self._update_progress, 100, "Analyse abgeschlossen")
    # --- ENDE KORREKTUR ---

    def _create_loading_window(self):
        self.loading_win = tk.Toplevel(self); self.loading_win.title("Ladevorgang"); self.loading_win.geometry("450x130"); self.loading_win.resizable(False, False); self.parent.update_idletasks(); x = self.parent.winfo_screenwidth() // 2 - self.loading_win.winfo_width() // 2; y = self.parent.winfo_screenheight() // 2 - self.loading_win.winfo_height() // 2; self.loading_win.geometry(f"+{x}+{y}"); self.loading_win.transient(self); self.loading_win.grab_set(); self.loading_label = ttk.Label(self.loading_win, text="Initialisiere...", font=("Helvetica", 10)); self.loading_label.pack(pady=(15, 5), padx=10, anchor="w"); self.loading_progress_bar = ttk.Progressbar(self.loading_win, orient="horizontal", mode="determinate"); self.loading_progress_bar.pack(fill=tk.X, expand=True, padx=10); self.percent_label = ttk.Label(self.loading_win, text="0%", font=("Helvetica", 10)); self.percent_label.pack(pady=5)

    def _update_progress(self, progress, filename):
        if self.loading_win:
             self.loading_win.lift()
             base_filename = os.path.basename(filename) if isinstance(filename, str) else str(filename)
             self.loading_label.config(text=f"{base_filename}") # Nur Text anzeigen
             self.loading_progress_bar['value'] = progress
             self.percent_label.config(text=f"{progress}%")
             self.loading_win.update_idletasks()

    def _check_thread(self, thread):
        if thread.is_alive():
            self.after(100, self._check_thread, thread)
        else:
            self.after(100, self._finalize_loading)

    def _finalize_loading(self):
        if self.loading_win:
            self.loading_win.destroy()
            self.loading_win = None

        if not self.raw_df.empty:
            self._update_treeview(self.raw_df)
            self.status_label.config(text=f"{len(self.raw_df)} Log-Einträge geladen.")
            messagebox.showinfo("Erfolg", f"Analyse abgeschlossen. {len(self.raw_df)} Log-Einträge gefunden.", parent=self)
        else:
            self._clear_treeview()
            self.status_label.config(text="Keine Log-Einträge gefunden.")
            messagebox.showwarning("Keine Daten", "Keine gültigen Log-Einträge in den gefundenen Dateien verarbeitet.", parent=self) # Meldung angepasst

    def _update_treeview(self, df):
        self._clear_treeview()
        cols_to_show = ["Timestamp", "Source", "IATA", "Klartext", "OriginalLog"]
        # Sicherstellen, dass die Spalten existieren, bevor darauf zugegriffen wird
        existing_cols = [col for col in cols_to_show if col in df.columns]
        if not existing_cols:
            print("WARNUNG: Keine der erwarteten Spalten im DataFrame gefunden.")
            return

        df_display = df[existing_cols].copy()

        # Zeitstempel formatieren, falls vorhanden
        if 'Timestamp' in df_display.columns:
            # Konvertiere sicherheitshalber nochmal zu datetime, falls nötig
            df_display['Timestamp'] = pd.to_datetime(df_display['Timestamp'], errors='coerce')
            # Zeilen mit NaT (Not a Time) werden als 'N/A' angezeigt
            ts_formatted = df_display['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S.%f').str[:-3]
            df_display['Timestamp'] = ts_formatted.fillna('N/A')
        else:
            df_display['Timestamp'] = 'N/A' # Füge leere Spalte hinzu, falls sie fehlt

        # Fehlende Spalten auffüllen, damit die Werte-Liste immer passt
        for col in cols_to_show:
            if col not in df_display.columns:
                 df_display[col] = 'N/A'

        # Stelle sicher, dass die Reihenfolge für `values` stimmt
        df_display = df_display[cols_to_show]

        for index, row in df_display.iterrows():
            self.tree.insert("", "end", iid=index, values=list(row))


    def _clear_treeview(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

    def _show_help_window(self):
        help_win = tk.Toplevel(self)
        help_win.title("Anleitung - MV3D Analyzer")
        help_win.geometry("800x600")
        help_win.transient(self); help_win.grab_set()
        text_area = scrolledtext.ScrolledText(help_win, wrap=tk.WORD, font=("Helvetica", 10), padx=10, pady=10)
        text_area.pack(expand=True, fill=tk.BOTH)
        text_area.insert(tk.INSERT, MV3D_HELP_TEXT)
        text_area.config(state="disabled")

    def _open_ftp_dialog(self):
        dialog = FTPDialog(self)
        ftp_details = dialog.show()
        if ftp_details:
            log_win = SFTPLogWindow(self)
            thread = threading.Thread(target=self._run_sftp_download, args=(ftp_details, log_win), daemon=True)
            thread.start()

    def _run_sftp_download(self, details, log_win):
        local_dir = os.path.join(os.getcwd(), "logs", "mv3d_download")
        os.makedirs(local_dir, exist_ok=True)

        host = details.get("host")
        port = details.get("port", 22)
        user = details.get("user")
        passwd = details.get("passwd")
        remote_dir = details.get("path")

        all_downloaded_files = []
        has_errors = False

        def log_callback(message):
            self.after(0, log_win.log, message)

        if not host:
            log_callback("FEHLER: Kein Host im FTP-Dialog angegeben.")
            self.after(3000, log_win.close_window)
            return

        log_callback(f"--- Starte Verbindung zu {host} ---")
        self.after(0, self.set_connection_status, "connected")

        client = SFTPClient(host, user, passwd, port)
        message, success = client.connect(log_callback)

        if success:
            log_callback(f"Erfolgreich mit {host} verbunden.")
            if not remote_dir:
                 log_callback(f"WARNUNG: Kein Remote-Pfad angegeben.")
                 message, downloaded = "", []
            else:
                log_callback(f"Starte Download von: {remote_dir}")
                message, downloaded = client.download_all_files_from_dir(remote_dir, local_dir, log_callback)

            if downloaded is False:
                has_errors = True
                log_callback(f"FEHLER beim Download von {host} ({remote_dir}): {message}")
                self.after(0, self.set_connection_status, "error")
            elif downloaded:
                 all_downloaded_files.extend(downloaded)
                 log_callback(f"Erfolgreich {len(downloaded)} Datei(en) von {host} heruntergeladen.")
            else:
                 log_callback(f"Keine Dateien in {remote_dir} gefunden.")

        else:
            has_errors = True
            log_callback(f"FEHLER bei der Verbindung zu {host}: {message}")
            self.after(0, self.set_connection_status, "error")

        log_callback(f"--- Trenne Verbindung zu {host} ---")
        client.disconnect()
        self.after(0, self.set_connection_status, "disconnected")

        if not all_downloaded_files and has_errors:
            log_callback("Download-Prozess mit Fehlern abgeschlossen.")
        elif all_downloaded_files:
            log_callback(f"Download abgeschlossen. {len(all_downloaded_files)} Datei(en) insgesamt.")
            log_callback("Starte Analyse der heruntergeladenen Dateien...")
            self.after(0, self.on_ftp_download_complete, all_downloaded_files)
        elif not has_errors:
            log_callback("Keine Dateien zum Herunterladen gefunden.")

        self.after(3000, log_win.close_window)


    def on_ftp_download_complete(self, downloaded_files):
        download_dir = os.path.join(os.getcwd(), "logs", "mv3d_download")
        messagebox.showinfo("Download Abgeschlossen",
                            f"{len(downloaded_files)} Datei(en) heruntergeladen nach:\n{download_dir}\n\nAnalyse wird gestartet.",
                            parent=self)
        self.current_directory = download_dir
        self._start_loading_process(download_dir)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        root = tk.Tk()
        app = MV3DApp(root)
        root.mainloop()
    except Exception as e:
        with open("mv3d_crash_report.log", "w", encoding='utf-8') as f:
            f.write("Ein kritischer Fehler ist in mv3d_app.py aufgetreten:\n\n")
            f.write(traceback.format_exc())