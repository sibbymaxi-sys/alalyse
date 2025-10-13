# ftp_client.py
import os
import paramiko
import fnmatch
from datetime import datetime

class SFTPClient:
    # ... __init__, connect, disconnect bleiben unverändert ...
    def __init__(self, host, user, passwd, port=22):
        self.host, self.user, self.passwd, self.port = host, user, passwd, int(port)
        self.ssh, self.sftp = None, None

    def connect(self, log_callback):
        try:
            if log_callback: log_callback(f"Stelle Verbindung zu {self.host} her...")
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(self.host, port=self.port, username=self.user, password=self.passwd, timeout=10)
            self.sftp = self.ssh.open_sftp()
            if log_callback: log_callback(f"Verbindung zu {self.host} erfolgreich.")
            return "SFTP-Verbindung erfolgreich hergestellt.", True
        except Exception as e:
            if log_callback: log_callback(f"FEHLER bei Verbindung zu {self.host}: {e}")
            return f"SFTP-Verbindungsfehler: {e}", False

    def disconnect(self):
        if self.sftp: self.sftp.close()
        if self.ssh: self.ssh.close()

    # GEÄNDERT: Die Hauptfunktion wird um die neue Regel erweitert
    def execute_download_rules(self, rules, local_dir, log_callback):
        if not self.sftp: return "Nicht verbunden.", []
        
        downloaded_paths = []
        log_callback(f"Beginne regelbasierten Download...")
        for rule in rules:
            rule_type = rule.get("type")
            
            if rule_type == "specific_file":
                _, path = self.download_single_file(rule["path"], local_dir, log_callback)
                if path: downloaded_paths.append(path)

            elif rule_type == "all_in_dir":
                _, paths = self.download_all_files_from_dir(rule["dir"], local_dir, log_callback)
                if paths: downloaded_paths.extend(paths)

            elif rule_type == "latest_with_pattern":
                _, path = self._download_latest_with_pattern(rule["dir"], rule["pattern"], local_dir, log_callback)
                if path: downloaded_paths.append(path)
            
            # NEU: Logik für die rotierenden Log-Dateien
            elif rule_type == "file_with_rotations":
                _, paths = self._download_file_with_rotations(rule["dir"], rule["basename"], local_dir, log_callback)
                if paths: downloaded_paths.extend(paths)
        
        return "Regeln abgearbeitet.", downloaded_paths

    # NEU: Diese Funktion implementiert die Suche nach rotierten Logs
    def _download_file_with_rotations(self, remote_dir, basename, local_dir, log_callback):
        """Sucht und lädt eine Basis-Datei und alle ihre nummerierten Rotationen."""
        if not self.sftp: return "Nicht verbunden.", []
        
        log_callback(f"Suche nach '{basename}' und rotierten Versionen in '{remote_dir}'...")
        downloaded_files = []
        try:
            files_in_dir = self.sftp.listdir(remote_dir)
            
            for filename in files_in_dir:
                # Prüft, ob der Dateiname exakt passt ODER mit ".<zahl>" rotiert wurde
                is_match = (filename.lower() == basename.lower())
                is_rotation = (filename.lower().startswith(basename.lower() + ".") and 
                               filename.split('.')[-1].isdigit())

                if is_match or is_rotation:
                    remote_path = os.path.join(remote_dir, filename).replace('\\', '/')
                    _, path = self.download_single_file(remote_path, local_dir, log_callback)
                    if path:
                        downloaded_files.append(path)

            if not downloaded_files:
                log_callback(f"-> Info: Keine Version von '{basename}' in '{remote_dir}' gefunden.")

            return "Suche nach Rotationen abgeschlossen.", downloaded_files
        except Exception as e:
            log_callback(f"-> FEHLER beim Suchen nach Rotationen in '{remote_dir}': {e}")
            return str(e), []

    # ... (Die restlichen Funktionen bleiben unverändert) ...
    def _download_latest_with_pattern(self, remote_dir, pattern, local_dir, log_callback):
        try:
            log_callback(f"Suche neueste Datei für '{pattern}*' in '{remote_dir}'...")
            files_in_dir = self.sftp.listdir_attr(remote_dir)
            latest_file_attr = None
            for attr in files_in_dir:
                if fnmatch.fnmatch(attr.filename, f"{pattern}*"):
                    if latest_file_attr is None or attr.st_mtime > latest_file_attr.st_mtime:
                        latest_file_attr = attr
            if latest_file_attr:
                remote_path = os.path.join(remote_dir, latest_file_attr.filename).replace('\\', '/')
                log_callback(f"-> Aktuellste Datei gefunden: {latest_file_attr.filename}")
                return self.download_single_file(remote_path, local_dir, log_callback)
            else:
                log_callback(f"-> Info: Kein passendes Muster '{pattern}*' in '{remote_dir}' gefunden.")
                return f"Kein Muster '{pattern}*' gefunden", None
        except Exception as e:
            log_callback(f"-> FEHLER beim Suchen nach Muster in '{remote_dir}': {e}")
            return str(e), None

    def download_single_file(self, remote_path, local_dir, log_callback):
        if not self.sftp: return "Nicht verbunden.", None
        try:
            filename = os.path.basename(remote_path)
            local_path = os.path.join(local_dir, filename)
            log_callback(f"Lade Datei: {remote_path}...")
            self.sftp.get(remote_path, local_path)
            log_callback(f"-> '{filename}' erfolgreich gespeichert.")
            return "Erfolg", local_path
        except FileNotFoundError:
            log_callback(f"-> Info: '{remote_path}' nicht gefunden, übersprungen.")
            return "Datei nicht gefunden", None
        except Exception as e:
            log_callback(f"-> FEHLER bei '{remote_path}': {e}")
            return str(e), None

    def download_all_files_from_dir(self, remote_dir, local_dir, log_callback):
        if not self.sftp: return "Nicht verbunden.", []
        downloaded_files = []
        try:
            files = self.sftp.listdir(remote_dir)
            log_callback(f"Lade {len(files)} Dateien aus Ordner: {remote_dir}...")
            for filename in files:
                remote_filepath = os.path.join(remote_dir, filename).replace('\\', '/')
                _, path = self.download_single_file(remote_filepath, local_dir, lambda msg: None)
                if path: downloaded_files.append(path)
            log_callback(f"-> {len(downloaded_files)} Dateien aus '{remote_dir}' erfolgreich geladen.")
            return "Erfolg", downloaded_files
        except Exception as e:
            log_callback(f"-> FEHLER beim Lesen von Ordner '{remote_dir}': {e}")
            return str(e), []