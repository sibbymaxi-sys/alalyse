# mv3d_log_parser.py
import re
import pandas as pd
from datetime import datetime

TS_PATTERN = re.compile(r"^([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)")
MV3D_RECONSTRUCTION_PATTERN = re.compile(r'Starting reconstruction of bag \[BagID: (\d+)\]')
BHS_DISPOSITION_PATTERN = re.compile(r'BagDispMgr: Sending bag disposition - (\d+);')
BHS_IATA_PATTERN = re.compile(r'IATA string: \"\s*([A-Za-z0-9_-]+)\s*\"')

def parse_line_to_klartext(line, bag_id, iata):
    if MV3D_RECONSTRUCTION_PATTERN.search(line):
        return f"[MV3D] Beginne Rekonstruktion für BagID {bag_id}."
    if BHS_DISPOSITION_PATTERN.search(line):
        disp_code = BHS_DISPOSITION_PATTERN.search(line).group(1)
        return f"[BHS] Sende Disposition-Code '{disp_code}' für IATA {iata}."
    return "Unbekanntes MV3D-Ereignis."

def parse_mv3d_log(file_path):
    log_records = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            ts_match = TS_PATTERN.search(line)
            if not ts_match: continue
            dt_object = datetime.strptime(ts_match.group(1), "%a %b %d %H:%M:%S.%f")
            bag_id_match = MV3D_RECONSTRUCTION_PATTERN.search(line)
            iata_match = BHS_IATA_PATTERN.search(line)
            bag_id = bag_id_match.group(1) if bag_id_match else "N/A"
            iata = iata_match.group(1) if iata_match else "N/A"
            if bag_id == "N/A" and iata == "N/A": continue
            klartext = parse_line_to_klartext(line, bag_id, iata)
            log_records.append({
                "Timestamp": dt_object, "BagID": bag_id, "IATA": iata,
                "Klartext": klartext, "OriginalLog": line.strip()
            })
    return pd.DataFrame(log_records)