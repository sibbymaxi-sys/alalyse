# mv3d_log_parser.py
# VERSION 2.3
# - HINZUGEFÜGT: Erkennt jetzt auch boot.log, yum.log und dmesg.
# - (Behält alle Fixes aus v2.2 bei)

import os
import re
import pandas as pd
import gzip
import shutil
from datetime import datetime
import warnings

try:
    from mv3d_error_definitions import ERROR_DEFINITIONS
except ImportError:
    print("WARNUNG: mv3d_error_definitions.py nicht gefunden. Verwende leere Fehlerliste.")
    ERROR_DEFINITIONS = {}

warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

class MV3DLogParser:
    def __init__(self):
        # 1. Definition der Parser-Map (ERWEITERT)
        self.PARSER_MAP = {
            'dpp': {
                'file_pattern': r'^(dpp\.log|dpp\.log\.\d+(\.gz)?)$',
                'parser_func': self._generic_parser,
                'system_tag': 'DPP'
            },
            'scs': {
                'file_pattern': r'^(scs\.log|scs\.log\.\d+(\.gz)?)$',
                'parser_func': self._generic_parser,
                'system_tag': 'SCS'
            },
            'bhs': {
                'file_pattern': r'^(bhs\.log|bhs\.log\.\d+(\.gz)?)$',
                'parser_func': self._generic_parser,
                'system_tag': 'BHS'
            },
            'fsm': {
                'file_pattern': r'^(fsm\.log|fsm\.log\.\d+(\.gz)?)$',
                'parser_func': self._generic_parser,
                'system_tag': 'FSM'
            },
            'optinet': {
                'file_pattern': r'^(optinet\.log|optinet\.log\.\d+(\.gz)?)$',
                'parser_func': self._generic_parser,
                'system_tag': 'OptiNet'
            },
            'plc': {
                'file_pattern': r'^(plc\.log|plc\.log\.\d+(\.gz)?)$',
                'parser_func': self._generic_parser,
                'system_tag': 'PLC'
            },
            'bms': {
                'file_pattern': r'^(bms\.log|bms\.log\.\d+(\.gz)?)$',
                'parser_func': self._generic_parser,
                'system_tag': 'BMS'
            },
            'iqt': {
                'file_pattern': r'^(iqt\.log|iqt\.log\.\d+(\.gz)?)$',
                'parser_func': self._generic_parser,
                'system_tag': 'IAC-IQT' 
            },
            'scanner_bag': {
                'file_pattern': r'^(scanner_bag\.log|scanner_bag\.log\.\d+(\.gz)?)$',
                'parser_func': self._generic_parser,
                'system_tag': 'IAC-Scanner'
            },
            'alg_logs': {
                'file_pattern': r'^(alg\d+_\d+|current)(\.gz)?$',
                'parser_func': self._generic_parser,
                'system_tag': 'IAC-ALG'
            },
            'scc_app': {
                'file_pattern': r'^(app\.log|app\.log\.\d+(\.gz)?)$',
                'parser_func': self._generic_parser,
                'system_tag': 'SCC-App'
            },
            'diagserv': {
                'file_pattern': r'^(diagserv_\d+-\d+-\d+_\d+)(\.gz)?$',
                'parser_func': self._generic_parser,
                'system_tag': 'DiagServ'
            },
            'diagnostics': {
                'file_pattern': r'^(Diagnostics_\d+-\d+-\d+_\d+)$', 
                'parser_func': self._generic_parser,
                'system_tag': 'Diagnostics'
            },
            
            # --- NEU HINZUGEFÜGT (v2.3) ---
            'sys_messages': {
                'file_pattern': r'^(messages|messages-\d{8})(\.gz)?$',
                'parser_func': self._generic_parser,
                'system_tag': 'System'
            },
            'secure': {
                'file_pattern': r'^(secure|secure-\d{8})(\.gz)?$',
                'parser_func': self._generic_parser, 
                'system_tag': 'System-Secure'
            },
            'boot': {
                'file_pattern': r'^(boot\.log|boot\.log-\d{8})(\.gz)?$', 
                'parser_func': self._generic_parser, 
                'system_tag': 'System-Boot'
            },
            'yum': {
                'file_pattern': r'^(yum\.log|yum\.log-\d{8})(\.gz)?$', 
                'parser_func': self._generic_parser, 
                'system_tag': 'System-Yum'
            },
            'dmesg': {
                'file_pattern': r'^(dmesg|dmesg\.log|dmesg-\d{8})(\.gz)?$', 
                'parser_func': self._generic_parser, 
                'system_tag': 'System-Dmesg'
            }
            # --- ENDE NEU ---
        }
        
        # 2. Vorkompilierte Regex-Muster (Logik von v2.1 - ist korrekt)
        self.ERROR_PATTERNS = self._compile_error_patterns()
        print(f"--- {len(self.ERROR_PATTERNS)} MV3D-Fehlermuster (v2.3) vorkompiliert. ---")

        self.TS_REGEX = re.compile(
            r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}(?:[.,]\d{3,6})?)'
            r'|((?:[A-Z][a-z]{2}\s+)?(?:[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})(?:[.,]\d{3,6})?)'
            r'|(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[.,]\d{3,6})?Z)'
        )
        
        self.BAG_ID_REGEX = re.compile(r'\b(0\d{9})\b')
        self.TRAY_ID_REGEX = re.compile(r'\[TRAY_ID=(\d+)\]')
        
        self.analysis_dir = None 
        self.assumed_year = datetime.now().year

    def _compile_error_patterns(self):
        # (Logik von v2.1 - ist korrekt)
        compiled = []
        if not ERROR_DEFINITIONS:
            return []
            
        for regex_str, details in ERROR_DEFINITIONS.items():
            try:
                pattern = re.compile(regex_str, re.IGNORECASE)
                
                category = "GENERIC" # Default
                if "FATAL" in regex_str.upper() or "E-STOP" in regex_str.upper() or r"mfc=16" in regex_str:
                    category = "E-STOP"
                elif "FAULT" in regex_str.upper() or "FAIL" in regex_str.upper() or "mfc=" in regex_str or "fault_cause" in regex_str:
                    category = "FAULT"
                elif "WARN" in regex_str.upper() or "limitSwitchWarning" in regex_str:
                    category = "WARNING"
                elif "BAG JAM" in regex_str.upper():
                    category = "BAG-JAM"
                elif "TIMEOUT" in regex_str.upper():
                    category = "TIMEOUT"
                elif "HVPS" in regex_str.upper() or "Arc count" in regex_str:
                    category = "HVPS"
                elif "BNA" in regex_str.upper() or "exceptions =" in regex_str:
                    category = "BNA"
                elif "disconnected" in regex_str.lower() or "Connection" in regex_str:
                     category = "COMM"
                elif "TEMP" in regex_str.upper():
                    category = "TEMP"
                elif "PLC" in regex_str.upper() or "XBDP" in regex_str.upper():
                    category = "PLC"
                elif "DPP" in regex_str.upper():
                    category = "DPP"
                elif "IAC" in regex_str.upper():
                    category = "IAC"
                
                compiled.append((pattern, details, category))
                
            except re.error as e:
                print(f"WARNUNG: Ungültiges Regex in mv3d_error_definitions.py ignoriert: {regex_str} -> {e}")
        return compiled

    def run_full_analysis(self, file_list, progress_callback, is_local=False):
        # (Funktion unverändert zu v2.0/v2.1)
        progress_callback(0, "Starte Analyse...")
        log_files_map = self._build_log_map_from_list(file_list)
        if not log_files_map:
            progress_callback(100, "Analyse fehlgeschlagen: Keine passenden Logs.")
            return pd.DataFrame(), pd.DataFrame()

        processed_files = {}
        if is_local:
            progress_callback(20, "Lokale Dateien werden direkt gelesen...")
            processed_files = log_files_map
            print(f"--- Analysiere {len(file_list)} lokale Dateien direkt (ohne Kopie) ---")
        else:
            progress_callback(20, "Bereite 'logs'-Verzeichnis vor...")
            self.analysis_dir = self._prepare_analysis_dir()
            progress_callback(30, "Kopiere FTP-Logs...")
            processed_files = self._copy_files_to_analysis_dir(log_files_map, progress_callback)
        
        if not processed_files:
            progress_callback(100, "Analyse fehlgeschlagen: Logs konnten nicht kopiert/gefunden werden.")
            return pd.DataFrame(), pd.DataFrame()

        all_incidents = []
        all_raw_entries = []
        
        total_parsers = len(processed_files)
        for i, (parser_name, files) in enumerate(processed_files.items()):
            parser_info = self.PARSER_MAP[parser_name]
            parser_func = parser_info['parser_func']
            system_tag = parser_info.get('system_tag', 'UNKNOWN') 
            
            for file_path in files:
                filename = os.path.basename(file_path)
                progress = 60 + int(((i + 1) / total_parsers) * 35)
                progress_callback(progress, f"Parse: {filename}")
                
                try:
                    incidents, raw_entries = parser_func(file_path, filename, system_tag)
                    all_incidents.extend(incidents)
                    all_raw_entries.extend(raw_entries)
                except Exception as e:
                    print(f"FEHLER: Parser {parser_name} fehlgeschlagen für Datei {filename}: {e}")

        progress_callback(95, "Kombiniere Ergebnisse...")

        if not all_raw_entries and not all_incidents:
            print("INFO: Analyse abgeschlossen, keine lesbaren Log-Einträge gefunden.")
            progress_callback(100, "Analyse abgeschlossen. Keine lesbaren Einträge gefunden.")
            return pd.DataFrame(), pd.DataFrame()
            
        incidents_df = pd.DataFrame(all_incidents) if all_incidents else pd.DataFrame()
        raw_df = pd.DataFrame(all_raw_entries) if all_raw_entries else pd.DataFrame()
        
        if not incidents_df.empty:
            incidents_df = incidents_df.sort_values(by="Timestamp").drop_duplicates()
            incidents_df.reset_index(drop=True, inplace=True)

        if not raw_df.empty:
            raw_df = raw_df.sort_values(by="Timestamp").drop_duplicates()
            raw_df.reset_index(drop=True, inplace=True)
        
        progress_callback(100, f"Analyse abgeschlossen. {len(incidents_df)} Ereignisse gefunden.")
        
        return incidents_df, raw_df

    # --- Datei-Vorbereitung (unverändert zu v2.0/v2.1) ---
    def _build_log_map_from_list(self, file_list):
        log_files_map = {}
        for file_path in file_list:
            file_name = os.path.basename(file_path)
            for parser_name, info in self.PARSER_MAP.items():
                if re.match(info['file_pattern'], file_name):
                    if parser_name not in log_files_map:
                        log_files_map[parser_name] = []
                    log_files_map[parser_name].append(file_path)
                    break 
        return log_files_map

    def _prepare_analysis_dir(self):
        base_path = os.getcwd()
        analysis_path = os.path.join(base_path, "logs")
        os.makedirs(analysis_path, exist_ok=True)
        print(f"--- Analyse-Verzeichnis erstellt/geprüft: {analysis_path}")
        return analysis_path

    def _copy_files_to_analysis_dir(self, log_files_map, progress_callback):
        processed_files = {}
        total_files = sum(len(files) for files in log_files_map.values())
        if total_files == 0: return {}
        copied_count = 0
        last_filename = "" 
        for parser_name, file_paths in log_files_map.items():
            for file_path in file_paths:
                last_filename = os.path.basename(file_path)
                try:
                    if not os.path.isfile(file_path):
                        print(f"WARNUNG: (FTP) Überspringe (nicht gefunden): {file_path}")
                        continue
                    if os.path.getsize(file_path) == 0:
                        print(f"WARNUNG: (FTP) Überspringe (0-Byte): {file_path}")
                        continue
                    dest_path = os.path.join(self.analysis_dir, os.path.basename(file_path))
                    if file_path.endswith(".gz"):
                        dest_path = dest_path[:-3] 
                        with gzip.open(file_path, 'rb') as f_in:
                            with open(dest_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                    else:
                        shutil.copy(file_path, dest_path)
                    if parser_name not in processed_files:
                        processed_files[parser_name] = []
                    processed_files[parser_name].append(dest_path) 
                except (FileNotFoundError, OSError) as e: 
                    print(f"WARNUNG: (FTP) Kopieren fehlgeschlagen {file_path}: {e}")
                copied_count += 1
                progress = 30 + int((copied_count / total_files) * 30)
                if last_filename:
                    progress_callback(progress, f"Kopiere: {last_filename}")
        return processed_files

    # --- 2. Haupt-Parsing-Logik (Logik von v2.1 - ist korrekt) ---
    def _parse_line(self, line, source_file, system):
        timestamp = self._get_timestamp(line)
        if timestamp is None:
            return None, None 
        
        line_clean = line.strip()
        bag_id = self._get_bag_id(line_clean)
        tray_id = self._get_tray_id(line_clean)
        incident = None
        line_lower = line_clean.lower()
        
        for pattern, details, category in self.ERROR_PATTERNS:
            match = pattern.search(line_lower)
            if match:
                incident = {
                    "Timestamp": timestamp, 
                    "Category": category, 
                    "Error": match.group(0), 
                    "SourceFile": source_file,
                    "BagID": bag_id, 
                    "TrayID": tray_id, 
                    "System": system,
                    "OriginalLog": line_clean 
                }
                break 
                
        raw_entry = {
            "Timestamp": timestamp, "SourceFile": source_file,
            "BagID": bag_id, "TrayID": tray_id,
            "System": system, "OriginalLog": line_clean
        }
        return incident, raw_entry

    def _get_timestamp(self, line):
        # (unverändert zu v2.0/v2.1)
        match = self.TS_REGEX.search(line)
        if not match: return None
        try:
            ts_str = None
            if match.group(1): # Format 1: YYYY-MM-DD HH:MM:SS
                ts_str = match.group(1).replace(',', '.') 
                if '.' in ts_str:
                    parts = ts_str.split('.')
                    ts_str = parts[0] + '.' + parts[1][:6]
                return pd.to_datetime(ts_str)
            elif match.group(2): # Format 2: [Wochentag] Monat Tag HH:MM:SS
                ts_str = match.group(2).replace(',', '.').replace('  ', ' ')
                ms_part = None
                if '.' in ts_str:
                    parts = ts_str.split('.')
                    ts_str = parts[0]
                    ms_part_str = parts[1][:6].ljust(6, '0')
                    ms_part = int(ms_part_str)
                fmt_with_weekday = '%a %b %d %H:%M:%S'
                fmt_no_weekday = '%b %d %H:%M:%S'
                dt = None
                try: dt = datetime.strptime(ts_str, fmt_with_weekday)
                except ValueError:
                    try: dt = datetime.strptime(ts_str, fmt_no_weekday)
                    except ValueError: return None
                dt = dt.replace(year=self.assumed_year)
                if ms_part: dt = dt.replace(microsecond=ms_part)
                return dt
            elif match.group(4): # Format 3: YYYY-MM-DDTHH:MM:SS.sssZ
                ts_str = match.group(4).replace(',', '.')
                return pd.to_datetime(ts_str)
        except Exception as e:
            return None
        return None

    def _get_bag_id(self, line):
        match = self.BAG_ID_REGEX.search(line)
        return match.group(1) if match else None

    def _get_tray_id(self, line):
        match = self.TRAY_ID_REGEX.search(line)
        return match.group(1) if match else None

    # --- 3. Spezifische Log-Parser ---
    def _generic_parser(self, file_path, source_file, system_tag):
        # (unverändert zu v2.0/v2.1)
        incidents, raw_entries = [], []
        try:
            if file_path.endswith(".gz"):
                f = gzip.open(file_path, 'rt', encoding='utf-8', errors='ignore')
            else:
                f = open(file_path, 'r', encoding='utf-8', errors='ignore')

            with f:
                for line in f:
                    incident, raw_entry = self._parse_line(line, source_file, system_tag)
                    if raw_entry:
                        raw_entries.append(raw_entry)
                    if incident:
                        incidents.append(incident)
        except (OSError, FileNotFoundError, gzip.BadGzipFile) as e:
            print(f"FEHLER: Datei konnte nicht gelesen werden (evtl. defekt oder Symlink): {file_path}. Fehler: {e}")
        return incidents, raw_entries