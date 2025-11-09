# ftp_client.py
import paramiko
import os
from datetime import datetime, timedelta

class SFTPClient:
    def __init__(self, host, user, pwd, port=22):
        self.host = host
        self.port = int(port)
        self.user = user
        self.pwd = pwd
        self.ssh = None
        self.sftp = None

    def connect(self, log_callback):
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(self.host, port=self.port, username=self.user, password=self.pwd, timeout=10)
            self.sftp = self.ssh.open_sftp()
            return "Verbindung erfolgreich.", True
        except Exception as e:
            log_callback(f"SFTP Verbindungsfehler: {e}")
            return str(e), False

    def disconnect(self):
        if self.sftp: self.sftp.close()
        if self.ssh: self.ssh.close()

    # --- NEUE FUNKTION (zum Auflisten) ---
    def list_all_files_from_dir(self, remote_paths, log_callback, date_filter=None):
        """
        Listet alle Dateien in den remote_paths auf, die dem Datumsfilter entsprechen.
        Gibt eine Liste von vollständigen Remote-Dateipfaden zurück.
        """
        if not self.sftp:
            log_callback("Keine SFTP-Verbindung.")
            return []

        all_matching_files = []
        
        # Datumsfilter-Logik
        start_date_ts = None
        if date_filter and date_filter.get("mode") == "days":
            try:
                days = int(date_filter.get("days", 2))
                end_date_dt = datetime.now()
                start_date_dt = end_date_dt - timedelta(days=days)
                # Konvertiere in Timestamp (Sekunden seit Epoche) für den Vergleich
                start_date_ts = start_date_dt.timestamp()
                log_callback(f"Datumsfilter aktiv: Suche Dateien neuer als {start_date_dt.strftime('%Y-%m-%d')}.")
            except ValueError:
                log_callback("Fehler im Datumsfilter (Tage). Ignoriere Filter.")
        
        for remote_dir in remote_paths:
            log_callback(f"Durchsuche Verzeichnis: {remote_dir}")
            try:
                # Verwende 'find' um rekursiv alle Dateien zu finden
                stdin, stdout, stderr = self.ssh.exec_command(f"find {remote_dir} -type f")
                file_list_raw = stdout.read().decode().splitlines()
                
                if not file_list_raw:
                    log_callback(f"Keine Dateien in {remote_dir} gefunden.")
                    continue

                for remote_filepath in file_list_raw:
                    remote_filepath = remote_filepath.strip()
                    if not remote_filepath:
                        continue
                    
                    try:
                        # Datumsfilter anwenden
                        if start_date_ts:
                            file_mtime_ts = self.sftp.stat(remote_filepath).st_mtime
                            if file_mtime_ts < start_date_ts:
                                # Datei ist zu alt, überspringen
                                continue
                        
                        # Wenn Filter passt (oder kein Filter aktiv), hinzufügen
                        all_matching_files.append(remote_filepath)
                        
                    except Exception as e_stat:
                        log_callback(f"Warnung: Datei-Info für {remote_filepath} nicht abrufbar (ignoriert): {e_stat}")

            except Exception as e_find:
                log_callback(f"Fehler beim Ausführen von 'find' auf {remote_dir}: {e_find}")
        
        return all_matching_files

    # --- NEUE FUNKTION (zum selektiven Download) ---
    def download_selected_files(self, file_list, local_dir, log_callback):
        """
        Lädt eine spezifische Liste von Dateien (file_list) herunter.
        """
        if not self.sftp:
            return "Keine SFTP-Verbindung.", []

        downloaded_files = []
        total = len(file_list)
        for i, remote_filepath in enumerate(file_list):
            try:
                filename = os.path.basename(remote_filepath)
                local_filepath = os.path.join(local_dir, filename)
                
                os.makedirs(os.path.dirname(local_filepath), exist_ok=True)
                
                log_callback(f"Lade herunter ({i+1}/{total}): {filename}")
                self.sftp.get(remote_filepath, local_filepath)
                downloaded_files.append(local_filepath)
            
            except Exception as e:
                log_callback(f"FEHLER beim Download von {remote_filepath}: {e}")
        
        if not downloaded_files:
            return "Keine Dateien konnten heruntergeladen werden.", []
        
        return f"{len(downloaded_files)} Dateien erfolgreich heruntergeladen.", downloaded_files

    # --- BESTEHENDE FUNKTION (unverändert für GateView) ---
    def download_all_files_from_dir(self, remote_dir, local_dir, log_callback, date_filter=None):
        """
        Lädt ALLE Dateien aus einem Verzeichnis herunter (rekursiv).
        Wird noch von GateViewApp verwendet.
        """
        if not self.sftp:
            return "Keine SFTP-Verbindung.", []

        downloaded_files = []
        
        start_date_ts = None
        if date_filter and date_filter.get("mode") == "days":
            try:
                days = int(date_filter.get("days", 2))
                end_date_dt = datetime.now()
                start_date_dt = end_date_dt - timedelta(days=days)
                start_date_ts = start_date_dt.timestamp()
                log_callback(f"Datumsfilter aktiv: Lade nur Dateien der letzten {days} Tage.")
            except ValueError:
                 log_callback("Fehler im Datumsfilter (Tage). Ignoriere Filter.")

        try:
            stdin, stdout, stderr = self.ssh.exec_command(f"find {remote_dir} -type f")
            file_list_raw = stdout.read().decode().splitlines()

            if not file_list_raw:
                log_callback("Keine Dateien im Verzeichnis gefunden.")
                return "Keine Dateien gefunden.", []

            total_files = len(file_list_raw)
            log_callback(f"{total_files} Dateien gefunden. Starte Download-Prüfung...")
            
            filtered_list = []
            
            # Filtere zuerst die Liste
            if start_date_ts:
                log_callback("Filtere Dateiliste basierend auf Datum...")
                for remote_filepath in file_list_raw:
                    remote_filepath = remote_filepath.strip()
                    if not remote_filepath:
                        continue
                    try:
                        file_mtime_ts = self.sftp.stat(remote_filepath).st_mtime
                        if file_mtime_ts >= start_date_ts:
                            filtered_list.append(remote_filepath)
                    except Exception:
                        continue # Datei ignorieren, wenn stat fehlschlägt
                log_callback(f"{len(filtered_list)} von {total_files} Dateien entsprechen dem Filter.")
            else:
                filtered_list = [fp.strip() for fp in file_list_raw if fp.strip()]

            # Lade die gefilterte Liste herunter
            for i, remote_filepath in enumerate(filtered_list):
                filename = os.path.basename(remote_filepath)
                local_filepath = os.path.join(local_dir, filename)

                try:
                    # log_callback(f"Lade herunter ({i+1}/{len(filtered_list)}): {filename}")
                    self.sftp.get(remote_filepath, local_filepath)
                    downloaded_files.append(local_filepath)
                
                except Exception as e_get:
                    log_callback(f"FEHLER beim Download von {filename}: {e_get}")

        except Exception as e_find:
            log_callback(f"Fehler beim Ausführen von 'find' auf {remote_dir}: {e_find}")
            return str(e_find), []

        if not downloaded_files:
            return "Keine Dateien entsprachen dem Filter oder Fehler beim Download.", []
        
        return f"{len(downloaded_files)} Dateien erfolgreich heruntergeladen.", downloaded_files