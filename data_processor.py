# data_processor.py
import pandas as pd
import re

def _unify_identifiers(df):
    """
    Erstellt eine Master-Zuordnungstabelle aus allen Quellen und füllt fehlende IDs auf,
    um eine saubere Verknüpfung zu gewährleisten.
    """
    if df.empty or 'IATA' not in df.columns or 'BagID' not in df.columns:
        return df

    # Schritt 1: Finde alle expliziten Verknüpfungen von BagID und IATA
    # Wir nehmen an, dass eine "echte" BagID immer mit '0' beginnt und 10 Zeichen lang ist
    associations = df[df['BagID'].str.match(r'0\d{9}', na=False)].dropna(subset=['IATA'])
    associations = associations[associations['IATA'] != 'NO_READ']
    
    if associations.empty:
        return df # Keine Verknüpfungen gefunden

    # Erstelle "Wörterbücher" für eine schnelle Suche
    bag_to_iata = associations.drop_duplicates(subset=['BagID']).set_index('BagID')['IATA']
    iata_to_bag = associations.drop_duplicates(subset=['IATA']).set_index('IATA')['BagID']

    # Schritt 2: Fülle die Lücken
    def fill_missing(row):
        # Fall A: BagID fehlt, aber IATA ist vorhanden -> fülle BagID auf
        if pd.isna(row['BagID']) and pd.notna(row['IATA']):
            row['BagID'] = iata_to_bag.get(row['IATA'])
        # Fall B: IATA fehlt, aber BagID ist vorhanden -> fülle IATA auf
        elif pd.notna(row['BagID']) and pd.isna(row['IATA']):
            row['IATA'] = bag_to_iata.get(row['BagID'])
        return row
    
    df = df.apply(fill_missing, axis=1)
    return df

def get_final_disposition(group):
    """Ermittelt die finale Entscheidung für einen Gepäck-Durchlauf."""
    op_decisions = group[group['Klartext'].str.contains("Finale Operator-Entscheidung", na=False)]
    if not op_decisions.empty:
        # Nimm die letzte Operator-Entscheidung
        last_decision_text = op_decisions.iloc[-1]['Klartext']
        return "CLEAR" if "CLEAR" in last_decision_text else "ALARM"
        
    machine_decisions = group[group['Klartext'].str.contains("Maschinelle Entscheidung", na=False)]
    if not machine_decisions.empty:
        # Nimm die letzte Maschinen-Entscheidung
        last_decision_text = machine_decisions.iloc[-1]['Klartext']
        return "CLEAR" if "CLEAR" in last_decision_text else "ALARM"
        
    if 'NO_READ' in group['IATA'].values:
        return "ALARM (NO_READ)"
        
    return "Unbekannt"

def get_operator(group):
    """Ermittelt den letzten Operator, der eine Entscheidung getroffen hat."""
    op_decisions = group[group['Klartext'].str.contains("Finale Operator-Entscheidung")]
    if not op_decisions.empty:
        last_decision_text = op_decisions.iloc[-1]['Klartext']
        match = re.search(r"von '([^']+)'", last_decision_text)
        if match:
            return match.group(1)
    return "N/A" # Wenn keine Operator-Entscheidung gefunden wurde

def get_correct_iata(series):
    """Findet die erste gültige IATA in einer Serie."""
    valid_iatas = series.dropna()
    valid_iatas = valid_iatas[valid_iatas != 'NO_READ']
    return valid_iatas.iloc[0] if not valid_iatas.empty else 'NO_READ'

def consolidate_journeys(df):
    """
    Fasst die Rohdaten zu einzigartigen Gepäck-Durchläufen zusammen.
    Nutzt jetzt die neue, saubere Verknüpfungslogik.
    """
    if df.empty: return pd.DataFrame()
    
    # Führe zuerst die saubere Verknüpfung durch
    unified_df = _unify_identifiers(df.copy())
    
    # Arbeite nur mit Einträgen, die jetzt eine gültige BagID haben
    valid_bags = unified_df.dropna(subset=['BagID']).copy()
    if valid_bags.empty: return pd.DataFrame()
    
    grouped = valid_bags.groupby('BagID')
    summary_list = []
    for bag_id, group in grouped:
        summary_list.append({
            'Timestamp': group['Timestamp'].min(), 
            'BagID': bag_id,
            'IATA': get_correct_iata(group['IATA']),
            'End-Status': get_final_disposition(group),
            'Operator': get_operator(group)
        })
        
    summary = pd.DataFrame(summary_list)
    return summary.sort_values(by='Timestamp').reset_index(drop=True)