# data_processor.py
import pandas as pd
import re

def get_end_status(df_group):
    # Priorisiere PLC "REJECT" als finales Ergebnis
    plc_reject = df_group[(df_group['Source'] == 'PLC') & (df_group['Klartext'].str.contains("REJECT", na=False))]
    if not plc_reject.empty:
        return "ALARM (PLC REJECT)"

    # Priorisiere OMS-Befehl
    oms_command = df_group[(df_group['Source'] == 'OMS') & (df_group['Klartext'].str.contains("Finaler Befehl", na=False))]
    if not oms_command.empty:
        return "CLEAR" if "CLEAR" in oms_command.iloc[-1]['Klartext'] else "ALARM"
        
    # Fallback auf Operator-Entscheidung
    op_decision = df_group[df_group['Klartext'].str.contains("Finale Operator-Entscheidung", na=False)]
    if not op_decision.empty:
        return "CLEAR" if "CLEAR" in op_decision.iloc[-1]['Klartext'] else "ALARM"

    # Fallback auf maschinelle Entscheidung
    machine_decision = df_group[df_group['Klartext'].str.contains("Maschinelle Entscheidung", na=False)]
    if not machine_decision.empty:
        if "ALARM" in machine_decision['Klartext'].str.cat():
            return "ALARM (Maschine)"
            
    return "CLEAR"

def get_operator(df_group):
    op_decisions = df_group[df_group['Klartext'].str.contains(r"von '([a-zA-Z0-9_]+)'", na=False)]
    if not op_decisions.empty:
        match = re.search(r"von '([^']+)'", op_decisions.iloc[-1]['Klartext'])
        if match:
            return match.group(1)
    return "N/A"

def find_scanner_journeys(df):
    """Findet alle Scanner/OMS-Reisen und weist ihnen eine sequenzielle IATA-Nummer zu."""
    scanner_df = df[df['Source'].isin(['Scanner', 'OMS'])].copy()
    if scanner_df.empty:
        return pd.DataFrame(), {}

    scanner_df = scanner_df.sort_values(by=['BagID', 'Timestamp'])
    time_threshold = pd.Timedelta(minutes=3)
    # Erstelle eine Reise-ID basierend auf Zeitlücken pro BagID
    scanner_df['journey_id'] = (scanner_df.groupby('BagID')['Timestamp'].diff() > time_threshold).cumsum()
    
    journeys = []
    journey_map = {} # Zum Speichern der rohen Daten für jeden Key
    
    for (bag_id, journey_id), group in scanner_df.groupby(['BagID', 'journey_id']):
        if bag_id == 'N/A': continue
        
        start_time = group['Timestamp'].min()
        iatas = group['IATA'][~group['IATA'].isin(['N/A', 'NO_READ'])].unique()
        primary_iata = iatas[0] if len(iatas) > 0 else "NO_READ"
        
        # Erstelle einen eindeutigen Schlüssel für diese Reise
        journey_key = f"{primary_iata}_{start_time.strftime('%Y%m%d%H%M%S')}"
        
        sources = sorted(group['Source'].unique())
        quelle = ' + '.join(sources)

        journeys.append({
            'Timestamp': start_time,
            'BagID': bag_id,
            'IATA': primary_iata,
            'Operator': get_operator(group),
            'End-Status': get_end_status(group),
            'Quelle': quelle,
            'journey_key': journey_key # Der Schlüssel zur Verknüpfung
        })
        
        # Speichere die Indizes der Rohdaten für diesen Schlüssel
        journey_map[journey_key] = group.index
        
    return pd.DataFrame(journeys), journey_map

def find_plc_journeys(df):
    """Findet alle PLC-Reisen und weist ihnen eine sequenzielle IATA-Nummer zu."""
    plc_df = df[df['Source'] == 'PLC'].copy()
    if plc_df.empty:
        return {}

    plc_df = plc_df.sort_values(by=['IATA', 'Timestamp'])
    time_threshold = pd.Timedelta(minutes=5) # 5 Min. Puffer für PLC-Aktivität
    # Erstelle eine Reise-ID basierend auf Zeitlücken pro IATA
    plc_df['journey_id'] = (plc_df.groupby('IATA')['Timestamp'].diff() > time_threshold).cumsum()
    
    plc_journey_map = {}
    for (iata, journey_id), group in plc_df.groupby(['IATA', 'journey_id']):
        if iata == 'N/A' or iata == 'NO_READ': continue
        
        if iata not in plc_journey_map:
            plc_journey_map[iata] = []
        
        # Füge die Indizes dieser PLC-Reise der Warteschlange für diese IATA hinzu
        plc_journey_map[iata].append(group.index)
        
    return plc_journey_map

def consolidate_journeys(raw_df):
    """
    Führt Scanner-, OMS- und PLC-Logs sequenziell zusammen.
    """
    if raw_df.empty:
        return pd.DataFrame()
        
    raw_df['Timestamp'] = pd.to_datetime(raw_df['Timestamp'])
    
    # Schritt 1: Finde alle Scanner/OMS-Reisen (Basis)
    scanner_journeys_df, scanner_map = find_scanner_journeys(raw_df)
    
    # Schritt 2: Finde alle PLC-Reisen (sequenzielle Warteschlange)
    plc_map = find_plc_journeys(raw_df)
    
    # Dieser DataFrame wird die finalen, kombinierten Reisen enthalten
    final_journeys_df = scanner_journeys_df.copy()
    
    # Erstelle eine neue Spalte im raw_df, um alle Logs einer Reise zuzuordnen
    raw_df['journey_key'] = None
    
    # Schritt 3: Die "Hochzeit"
    for i, journey in final_journeys_df.iterrows():
        journey_key = journey['journey_key']
        iata = journey['IATA']
        
        # 1. Ordne die Scanner/OMS-Logs zu
        raw_df.loc[scanner_map[journey_key], 'journey_key'] = journey_key
        
        # 2. Finde die nächste passende PLC-Reise
        if iata in plc_map and plc_map[iata]:
            # Nimm die erste verfügbare PLC-Reise für diese IATA und entferne sie aus der Warteschlange
            plc_indices = plc_map[iata].pop(0) 
            
            # Ordne diese PLC-Logs derselben Reise zu
            raw_df.loc[plc_indices, 'journey_key'] = journey_key
            
            # Aktualisiere die "Quelle"-Spalte
            final_journeys_df.loc[i, 'Quelle'] = f"{journey['Quelle']} + PLC"
            
            # Optional: Bewerte den End-Status neu, jetzt MIT PLC-Daten
            full_journey_group = raw_df[raw_df['journey_key'] == journey_key]
            final_journeys_df.loc[i, 'End-Status'] = get_end_status(full_journey_group)

    # Schritt 4: Füge verbleibende PLC-Logs (ohne Scanner-Partner) hinzu
    if plc_map:
        unmatched_plc_journeys = []
        for iata, journey_list in plc_map.items():
            for plc_indices in journey_list:
                group = raw_df.loc[plc_indices]
                start_time = group['Timestamp'].min()
                journey_key = f"{iata}_{start_time.strftime('%Y%m%d%H%M%S')}"
                raw_df.loc[plc_indices, 'journey_key'] = journey_key
                
                unmatched_plc_journeys.append({
                    'Timestamp': start_time,
                    'BagID': 'N/A',
                    'IATA': iata,
                    'Operator': 'N/A',
                    'End-Status': get_end_status(group),
                    'Quelle': 'PLC (Allein)',
                    'journey_key': journey_key
                })
        if unmatched_plc_journeys:
            final_journeys_df = pd.concat([final_journeys_df, pd.DataFrame(unmatched_plc_journeys)], ignore_index=True)
            
    final_journeys_df.sort_values(by='Timestamp', inplace=True)
    return final_journeys_df[['Timestamp', 'BagID', 'IATA', 'Operator', 'End-Status', 'Quelle', 'journey_key']]