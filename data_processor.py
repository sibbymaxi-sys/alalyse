# data_processor.py
import pandas as pd
import re

def _create_intelligent_analysis(group):
    """
    Sucht nach bekannten Fehlerketten und fügt interpretierende [ANALYSE]-Einträge hinzu.
    """
    new_events = []
    # Muster 1: Hardware-Problem führt zu No Read
    if "KRITISCHER HARDWARE-FEHLER" in group['Klartext'].values and "NO_READ" in group['IATA'].values:
        error_time = group[group['Klartext'].str.contains("HARDWARE-FEHLER")].iloc[0]['Timestamp']
        new_events.append({
            "Timestamp": error_time + pd.Timedelta(milliseconds=1),
            "Source": "Analyse",
            "Klartext": '[ANALYSE] Fehlerkette erkannt: Ein Hardware-Problem (z.B. DCS-Datenstau) war wahrscheinlich die Ursache für den "NO_READ".'
        })
    # Muster 2: Timeout führt zu Maschinen-Alarm
    if "Zeitüberschreitung" in group['Klartext'].values and "Maschinelle Entscheidung: ALARM" in group['Klartext'].values:
        error_time = group[group['Klartext'].str.contains("Zeitüberschreitung")].iloc[0]['Timestamp']
        new_events.append({
            "Timestamp": error_time + pd.Timedelta(milliseconds=1),
            "Source": "Analyse",
            "Klartext": '[ANALYSE] Fehlerkette erkannt: Ein Timeout (z.B. bei der Operator-Entscheidung) hat einen automatischen Maschinen-Alarm ausgelöst.'
        })
    if new_events:
        analysis_df = pd.DataFrame(new_events)
        for col in group.columns:
            if col not in analysis_df.columns:
                analysis_df[col] = pd.NaT if pd.api.types.is_datetime64_any_dtype(group[col]) else None
        return pd.concat([group, analysis_df]).sort_values(by="Timestamp").reset_index(drop=True)
    return group

def _unify_identifiers(df):
    """
    Vereinheitlicht IDs über eine Master-Zuordnungstabelle.
    """
    if df.empty or 'Source' not in df.columns:
        return df
    map_list = []
    if 'IATA' in df.columns and 'BagID' in df.columns:
        scanner_df = df[df['Source'].str.contains('Scanner', case=False)].dropna(subset=['BagID', 'IATA'])
        if not scanner_df.empty:
            map_list.append(scanner_df[['BagID', 'IATA']])
    if 'OriginalLog' in df.columns:
        oms_df = df[df['Source'].str.upper() == 'OMS'].copy()
        if not oms_df.empty:
            extracted = oms_df['OriginalLog'].str.extract(r"Bag '(\w+)' has IATA L='(\w+)'")
            extracted.columns = ['BagID', 'IATA']
            map_list.append(extracted.dropna())
    if not map_list:
        return df
    master_map = pd.concat(map_list).drop_duplicates()
    bag_to_iata_map = master_map.drop_duplicates(subset=['BagID']).set_index('BagID')['IATA']
    iata_to_bag_map = master_map.drop_duplicates(subset=['IATA']).set_index('IATA')['BagID']
    df['BagID'] = df.apply(lambda row: iata_to_bag_map.get(row['IATA'], row.get('BagID')) if pd.isna(row.get('BagID')) and pd.notna(row.get('IATA')) else row.get('BagID'), axis=1)
    df['IATA'] = df.apply(lambda row: bag_to_iata_map.get(row['BagID'], row.get('IATA')) if pd.isna(row.get('IATA')) and pd.notna(row.get('BagID')) else row.get('IATA'), axis=1)
    return df

def consolidate_journeys(df):
    """
    Fasst die Rohdaten zu einzigartigen Gepäck-Durchläufen zusammen.
    """
    if df.empty:
        return pd.DataFrame()
    df = _unify_identifiers(df)
    journeys = []
    df_grouped = df.dropna(subset=['BagID'])
    for bag_id, group in df_grouped.groupby('BagID'):
        group = _create_intelligent_analysis(group)
        first_event = group.iloc[0]
        iata_series = group['IATA'][(group['IATA'].notna()) & (~group['IATA'].isin(['N/A', 'NO_READ']))]
        iata = iata_series.unique()[0] if len(iata_series.unique()) > 0 else "NO_READ"
        final_decision = "N/A"
        op_dec = group[group['Klartext'].str.contains("Finale Operator-Entscheidung|Späte Operator-Entscheidung", na=False)]
        if not op_dec.empty:
            match = re.search(r":\s*(.+)", op_dec.iloc[-1]['Klartext'])
            if match: final_decision = match.group(1).replace("**", "")
        else:
            mach_dec = group[group['Klartext'].str.contains("Maschinelle Entscheidung", na=False)]
            if not mach_dec.empty:
                match = re.search(r":\s*(.+)", mach_dec.iloc[-1]['Klartext'])
                if match: final_decision = match.group(1).replace("**", "")
        if final_decision == "N/A" and iata == "NO_READ":
            final_decision = "NO_READ"
        operator = "N/A"
        if 'Operator' in group.columns:
            valid_operators = group['Operator'].dropna()
            if not valid_operators.empty:
                operator = valid_operators.iloc[-1]
        journeys.append({'BagID': bag_id, 'IATA': iata, 'Timestamp': first_event['Timestamp'], 'End-Entscheidung': final_decision, 'Operator': operator})
    return pd.DataFrame(journeys).sort_values(by="Timestamp").reset_index(drop=True)