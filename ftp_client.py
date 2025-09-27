# sftp_client.py (vorher ftp_client.py)
import os
import paramiko

class SFTPClient:
    def __init__(self, host, user, passwd, port=22):
        self.host = host; self.user = user; self.passwd = passwd; self.port = port
        self.ssh = None; self.sftp = None

    def connect(self, progress_callback=None):
        try:
            if progress_callback: progress_callback(f"Stelle Verbindung zu {self.host} her...")
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(self.host, port=self.port, username=self.user, password=self.passwd, timeout=10)
            self.sftp = self.ssh.open_sftp()
            if progress_callback: progress_callback(f"Verbindung zu {self.host} erfolgreich.")
            return "SFTP-Verbindung erfolgreich hergestellt.", True
        except Exception as e:
            if progress_callback: progress_callback(f"FEHLER bei Verbindung zu {self.host}: {e}")
            self.ssh = None; self.sftp = None
            return f"SFTP-Verbindungsfehler: {e}", False

    def download_logs_from_paths(self, remote_paths_dict, local_dir, progress_callback=None):
        if not self.sftp: return "Keine SFTP-Verbindung.", []
        if not os.path.exists(local_dir): os.makedirs(local_dir)
        downloaded_files_paths = []; total_downloaded = 0
        try:
            for log_type, remote_path in remote_paths_dict.items():
                if not remote_path: continue
                if progress_callback: progress_callback(f"Durchsuche Verzeichnis: {remote_path}...")
                try:
                    files_in_dir = self.sftp.listdir(remote_path)
                    for filename in files_in_dir:
                        remote_filepath = os.path.join(remote_path, filename).replace('\\', '/')
                        local_filepath = os.path.join(local_dir, filename)
                        if progress_callback: progress_callback(f"Lade herunter: {filename}")
                        self.sftp.get(remote_filepath, local_filepath)
                        downloaded_files_paths.append(local_filepath); total_downloaded += 1
                except FileNotFoundError: continue
            return f"{total_downloaded} Datei(en) erfolgreich heruntergeladen.", downloaded_files_paths
        except Exception as e:
            if progress_callback: progress_callback(f"Download-Fehler: {e}")
            return f"SFTP-Download-Fehler: {e}", []

    def disconnect(self):
        if self.sftp: self.sftp.close()
        if self.ssh: self.ssh.close()

    def download_files(self, remote_files, local_dir, progress_callback=None):
        if not self.sftp: return "Keine SFTP-Verbindung.", []
        if not os.path.exists(local_dir): os.makedirs(local_dir)
        downloaded = []
        try:
            for remote_file in remote_files:
                filename = os.path.basename(remote_file)
                local_path = os.path.join(local_dir, filename)
                if progress_callback: progress_callback(f"Lade herunter: {filename}")
                self.sftp.get(remote_file, local_path)
                downloaded.append(local_path)
            return f"{len(downloaded)} Datei(en) erfolgreich heruntergeladen.", downloaded
        except Exception as e:
            if progress_callback: progress_callback(f"Download-Fehler: {e}")
            return f"SFTP-Download-Fehler: {e}", []