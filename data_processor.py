# data_processor.py
print("--- [V23-FIX] data_processor.py wird geladen (Neue PLC-Konsolidierung, Kein UTC) ... ---")

import pandas as pd
import re
from datetime import timedelta

# Spalten, die in Tab 1 angezeigt werden (wie von dir gewünscht)
FINAL_JOURNEY_COLS = [
    'Timestamp', 'IATA', 'BagID', 'Source', 
    'Operator', 'Decision', 'Device'
]

# --- NEUE SPALTEN FÜR TAB 2 (SPS-Journeys) ---
FINAL_PLC_JOURNEY_COLS = [
    'Timestamp', 'IATA', 'Klartext', 'Decision'
]
# ---------------------------------------------

# --- HINWEIS: _standardize_timestamps_to_utc() entfernt (Kein UTC) ---


def find_bag_id(group):
    """ Ignoriert N/A und NO_READ. """
    valid_bag_id = group['BagID'][~group['BagID'].isin(['N/A', 'NO_READ'])].unique()
    return valid_bag_id[0] if len(valid_bag_id) > 0 else 'N/A'

def create_journey_summary(group, journey_key, first_row):
    """ Erstellt die Zusammenfassungszeile (für Tab 1). """
    valid_iatas = group['IATA'][~group['IATA'].isin(['N/A', 'NO_READ'])].unique()
    iata = valid_iatas[0] if len(valid_iatas) > 0 else 'NO_READ'
    
    bag_id = find_bag_id(group)
    
    # --- Logik für "Source" ---
    sources_in_group = group['Source'].unique()
    if 'OMS' in sources_in_group and 'Scanner' in sources_in_group:
        source = "Scanner + OMS"
    elif 'OMS' in sources_in_group:
        source = "OMS"
    else:
        source = "Scanner"
    
    decision = 'N/A'
    machine_dec_df = group[group['Klartext'].str.contains("Maschinelle Entscheidung", na=False)]
    if not machine_dec_df.empty:
        last_dec_text = machine_dec_df.iloc[-1]['Klartext']
        match = re.search(r":\s*\*{0,2}(.*?)\*{0,2}$", last_dec_text)
        if match: decision = match.group(1)

    op = 'N/A'
    # SUCHT JETZT NACH BEIDEN (Finale... oder Operator...)
    op_dec_df = group[group['Klartext'].str.contains("Operator-Entscheidung", na=False)]
    if not op_dec_df.empty:
        last_op_text = op_dec_df.iloc[-1]['Klartext']
        match = re.search(r"von '([a-zA-Z0-9_]+)'", last_op_text)
        if match: op = match.group(1)
            
    # Gerät (CCT) holen
    device = 'N/A'
    # Fix: Stelle sicher, dass 'Device' existiert, bevor darauf zugegriffen wird
    if 'Device' in group.columns:
        valid_devices = group['Device'][~group['Device'].isin(['N/A', 'N/Aa'])].unique()
        if len(valid_devices) > 0:
            device = valid_devices[0]
    else:
        device = first_row.get('Device', 'N/A')


    summary = {
        'Timestamp': first_row['Timestamp'],
        'IATA': iata,
        'BagID': bag_id,
        'Source': source,
        'Klartext': "Journey", # Wird nicht mehr angezeigt
        'journey_key': journey_key, # Wird nicht mehr angezeigt
        'Severity': 'N/A', # Wird nicht mehr angezeigt
        'Operator': op,
        'Decision': decision,
        'Device': device 
    }
    return summary

def create_single_entry_journeys(non_journey_logs):
    """ 
    Wandelt "Waisen"-Logs (ohne klaren Key) in eine DataFrame-Struktur um.
    """
    if non_journey_logs.empty:
        return pd.DataFrame(columns=FINAL_JOURNEY_COLS)

    single_entries_df = non_journey_logs.copy()
    
    single_entries_df['journey_key'] = single_entries_df.apply(
        lambda row: f"SINGLE_{row['Timestamp']}_{row.name}", axis=1
    )
    single_entries_df['Severity'] = 'N/A'
    single_entries_df['Operator'] = 'N/A'
    single_entries_df['Decision'] = 'N/A'
    if 'Device' not in single_entries_df.columns:
        single_entries_df['Device'] = 'N/A'
    
    return single_entries_df[FINAL_JOURNEY_COLS]

def get_journey_key(group, time_threshold=timedelta(minutes=3)):
    if group.empty:
        return None
    
    valid_bag_ids = group['BagID'][~group['BagID'].isin(['N/A', 'NO_READ'])].unique()
    if len(valid_bag_ids) > 0:
        return valid_bag_ids[0]
    
    valid_iatas = group['IATA'][~group['IATA'].isin(['N/A', 'NO_READ'])].unique()
    if len(valid_iatas) > 0:
        return valid_iatas[0]
    
    return None

def add_journey_keys_to_raw_df(raw_df, time_threshold=timedelta(minutes=3)):
    """
    Fügt eine 'journey_key'-Spalte zum rohen DataFrame hinzu.
    """
    if raw_df.empty:
        return raw_df
        
    df = raw_df.copy()
    df['journey_key'] = None
    
    # 1. Verarbeite alle Zeilen, die eine BagID haben
    bag_id_mask = ~df['BagID'].isin(['N/A', 'NO_READ']) & df['BagID'].notna()
    bag_id_groups = df[bag_id_mask].groupby('BagID')
    
    for bag_id, group in bag_id_groups:
        time_diffs = group['Timestamp'].diff().fillna(timedelta(0))
        time_splits = (time_diffs > time_threshold).cumsum()
        df.loc[group.index, 'journey_key'] = time_splits.apply(lambda x: f"{bag_id}_{x}")

    # 2. Verarbeite verbleibende Zeilen, die *nur* eine IATA haben
    remaining_mask = df['journey_key'].isna()
    iata_only_mask = remaining_mask & (~df['IATA'].isin(['N/A', 'NO_READ']) & df['IATA'].notna())
    
    iata_groups = df[iata_only_mask].groupby('IATA')
    
    for iata, group in iata_groups:
        time_diffs = group['Timestamp'].diff().fillna(timedelta(0))
        time_splits = (time_diffs > time_threshold).cumsum()
        df.loc[group.index, 'journey_key'] = time_splits.apply(lambda x: f"{iata}_{x}")

    return df

# --- HAUPTFUNKTION (Scanner/OMS) ---

def consolidate_journeys(raw_df):
    """
    Konsolidiert Scanner/OMS-Logs (für Tab 1).
    GIBT ZURÜCK: (journeys_df, raw_df)
    """
    if raw_df.empty:
        return pd.DataFrame(columns=FINAL_JOURNEY_COLS), raw_df
        
    print(f"--- [V23-FIX] data_processor: Starte Scanner/OMS-Konsolidierung mit {len(raw_df)} Roh-Einträgen.")
    
    # Schritt 1: Sortiere nach Zeit (Zeitstempel sind bereits NAIVE)
    raw_df = raw_df.sort_values(by="Timestamp").reset_index(drop=True)

    # Schritt 2: Finde Zeit-basierte Gruppen (Journeys)
    raw_df = add_journey_keys_to_raw_df(raw_df)

    # 3. Filtere alle Nicht-Scanner/OMS-Quellen heraus
    allowed_sources = ['Scanner', 'OMS']
    
    journey_logs = raw_df[
        pd.notna(raw_df['journey_key']) & 
        raw_df['Source'].isin(allowed_sources)
    ].copy()
    
    non_journey_logs = raw_df[
        pd.isna(raw_df['journey_key']) & 
        raw_df['Source'].isin(allowed_sources)
    ].copy()

    # 5. Verarbeite die "Reisen" (Journeys)
    journey_summaries = []
    
    if not journey_logs.empty:
        journey_logs.sort_values(by='Timestamp', inplace=True)
        grouped = journey_logs.groupby('journey_key')
        
        for key, group in grouped:
            first_row = group.iloc[0]
            summary = create_journey_summary(group, key, first_row)
            journey_summaries.append(summary)

    journeys_df = pd.DataFrame(journey_summaries)

    # 6. Verarbeite die "Einzeleinträge" (Waisen-Logs)
    single_entries_df = create_single_entry_journeys(non_journey_logs)

    # 7. Kombiniere beide DataFrames
    final_journeys_df = pd.concat([journeys_df, single_entries_df], ignore_index=True)

    # 8. Finale Bereinigung und Sortierung
    if not final_journeys_df.empty:
        final_journeys_df.sort_values(by="Timestamp", inplace=True)
    
    print(f"--- [V23-FIX] data_processor: Konsolidierung abgeschlossen. {len(final_journeys_df)} Scanner/OMS Journeys gefunden.")
    
    return final_journeys_df[FINAL_JOURNEY_COLS], raw_df

# --- NEUE FUNKTION (für SPS-Journeys, Tab 2) ---

def consolidate_plc_journeys(plc_raw_df):
    """
    Konsolidiert die geparsten SPS-Journey-Logs (für Tab 2).
    Gruppiert nach IATA und fasst den Vorgang zusammen.
    
    GIBT ZURÜCK: (plc_journeys_df)
    """
    if plc_raw_df.empty:
        return pd.DataFrame(columns=FINAL_PLC_JOURNEY_COLS)
        
    print(f"--- [V23-FIX] data_processor: Starte PLC-Konsolidierung mit {len(plc_raw_df)} Roh-Einträgen.")
    
    # 1. Sortiere nach Zeit
    plc_raw_df = plc_raw_df.sort_values(by="Timestamp").reset_index(drop=True)
    
    # 2. Finde "Reisen" (Journeys)
    #    Wir definieren eine Reise als alle Logs mit derselben IATA,
    #    die nicht weiter als 5 Minuten auseinander liegen.
    valid_iata_mask = plc_raw_df['IATA'] != 'N/A'
    df_valid = plc_raw_df[valid_iata_mask].copy()
    
    time_threshold = timedelta(minutes=5)
    
    # Gruppiere nach IATA
    iata_groups = df_valid.groupby('IATA')
    key_list = []
    
    for iata, group in iata_groups:
        time_diffs = group['Timestamp'].diff().fillna(timedelta(0))
        time_splits = (time_diffs > time_threshold).cumsum()
        keys = time_splits.apply(lambda x: f"{iata}_{x}")
        key_list.append(keys)

    if not key_list:
        print("--- [V23-FIX] data_processor: Keine gültigen IATA-Gruppen für PLC-Konsolidierung gefunden.")
        return pd.DataFrame(columns=FINAL_PLC_JOURNEY_COLS)
        
    df_valid['journey_key'] = pd.concat(key_list)

    # 3. Fasse die Journeys zusammen
    journey_summaries = []
    
    if not df_valid.empty:
        grouped = df_valid.groupby('journey_key')
        
        for key, group in grouped:
            first_row = group.iloc[0]
            iata = first_row['IATA']
            
            # Finde die finale Entscheidung für diese IATA
            decision = 'N/A'
            final_dec_df = group[group['Klartext'].str.contains("Finale Entscheidung", na=False)]
            if not final_dec_df.empty:
                match = re.search(r"Finale Entscheidung.*:\s*(\S+)", final_dec_df.iloc[-1]['Klartext'])
                if match:
                    decision = match.group(1)
            
            # Finde die Operator-Entscheidung (falls vorhanden)
            op_dec_df = group[group['Klartext'].str.contains("Operator-Entscheidung", na=False)]
            if not op_dec_df.empty:
                 match = re.search(r"Operator-Entscheidung.*ist\s*(\S+)", op_dec_df.iloc[-1]['Klartext'])
                 if match:
                    decision = f"{match.group(1)} (Operator)"

            summary = {
                'Timestamp': first_row['Timestamp'],
                'IATA': iata,
                'Klartext': f"SPS-Vorgang für Wanne {iata}", # Zusammenfassung
                'Decision': decision
            }
            journey_summaries.append(summary)

    final_journeys_df = pd.DataFrame(journey_summaries)

    if not final_journeys_df.empty:
        final_journeys_df.sort_values(by="Timestamp", inplace=True)
        
    print(f"--- [V23-FIX] data_processor: PLC-Konsolidierung abgeschlossen. {len(final_journeys_df)} SPS-Journeys gefunden.")
    
    return final_journeys_df[FINAL_PLC_JOURNEY_COLS]