# log_previewer.py
import os
import re
from datetime import datetime

# Regex, das alle bekannten Zeitstempel-Formate abdeckt
TIMESTAMP_REGEX = re.compile(
    r"^([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2})|"  # Format: Fri Sep 19 13:58:26
    r"^(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})|"                      # Format: 2025-09-21 20:10:23
    r"^(\d{14})"                                                   # Format: 20250921201023
)

# Zugehörige Datumsformate für die Konvertierung
DATE_FORMATS = [
    "%a %b %d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y%m%d%H%M%S"
]

def get_timestamp_from_line(line):
    """ Versucht, aus einer Zeile einen Zeitstempel mit einem der bekannten Formate zu extrahieren. """
    match = TIMESTAMP_REGEX.search(line)
    if not match:
        return None
    
    ts_str = next((g for g in match.groups() if g is not None), None)
    if not ts_str:
        return None

    for fmt in DATE_FORMATS:
        try:
            # Füge ein Dummy-Jahr hinzu, wenn es fehlt, um es parsen zu können
            if len(ts_str) == 19 and ts_str[4] != '-': # Format ohne Jahr
                 dt_no_year = datetime.strptime(ts_str, fmt)
                 # Wir nehmen das aktuelle Jahr an, da die genaue Bestimmung hier zu aufwändig ist
                 return dt_no_year.replace(year=datetime.now().year)
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None

def get_log_file_daterange_and_count(file_path, buffer_size=8192):
    """ Findet den ersten/letzten Zeitstempel UND zählt die Zeilen. """
    line_count = 0
    first_ts, last_ts = None, None
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Finde ersten Zeitstempel und zähle Zeilen
            for i, line in enumerate(f):
                line_count = i + 1
                if not first_ts:
                    ts = get_timestamp_from_line(line)
                    if ts: first_ts = ts
            
            # Finde letzten Zeitstempel (effizient)
            f.seek(0) 
            try:
                f.seek(max(0, os.path.getsize(file_path) - buffer_size))
                last_chunk = f.read(buffer_size)
                for line in reversed(last_chunk.splitlines()):
                    ts = get_timestamp_from_line(line)
                    if ts:
                        last_ts = ts
                        break
            except (IOError, OSError): pass
            
            return first_ts, last_ts if last_ts else first_ts, line_count
    except Exception:
        return None, None, 0

def preview_log_directory(dir_path, parser_map):
    files_to_check = []
    for root, _, files in os.walk(dir_path):
        for file in files:
            if file in parser_map:
                files_to_check.append(os.path.join(root, file))

    if not files_to_check: return None, None, 0

    min_date, max_date, total_entries = None, None, 0
    for file in files_to_check:
        first, last, count = get_log_file_daterange_and_count(file)
        total_entries += count
        if first and (min_date is None or first < min_date):
            min_date = first
        if last and (max_date is None or last > max_date):
            max_date = last
            
    return min_date, max_date, total_entries