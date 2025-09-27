# data_processor.py
import pandas as pd
import re

def link_iata_to_oms(df):
    associations = df[(df['IATA'] != "N/A") & (df['IATA'] != "NO_READ")].groupby('BagID').agg(
        IATA=('IATA', 'first'), StartTime=('Timestamp', 'min'), EndTime=('Timestamp', 'max')
    ).reset_index()
    for index, row in df[(df['BagID'] == "N/A") & (df['IATA'] != "N/A")].iterrows():
        row_iata, row_ts = row['IATA'], row['Timestamp']
        possible_matches = associations[associations['IATA'] == row_iata]
        for _, assoc_row in possible_matches.iterrows():
            if assoc_row['StartTime'] <= row_ts <= assoc_row['EndTime']:
                df.loc[index, 'BagID'] = assoc_row['BagID']; break
    return df

def get_correct_iata(series):
    valid_iatas = series[(series != 'NO_READ') & (series != 'N/A')]
    return valid_iatas.iloc[0] if not valid_iatas.empty else 'NO_READ'

def get_final_disposition(group):
    if get_correct_iata(group['IATA']) == 'NO_READ': return "ALARM (NO_READ)"
    if "überschrieben" in group['Klartext'].str.cat(): return "ALARM (EDS Override)"
    op_decisions = group['Klartext'][group['Klartext'].str.contains("Finale Operator-Entscheidung")]
    if not op_decisions.empty:
        last_decision = op_decisions.iloc[-1]
        if "CLEAR" in last_decision: return "Freigegeben (Operator)"
        elif "ALARM" in last_decision: return "Alarm (Operator)"
    machine_decisions = group['Klartext'][group['Klartext'].str.contains("Maschinelle.*(?:LTR|EDS)", regex=True)]
    if not machine_decisions.empty:
        if "ALARM" in machine_decisions.iloc[-1]: return "Alarm (Maschine)"
        else: return "Freigegeben (Maschine)"
    return "Unbekannt"

def get_operator(group):
    """ **NEU:** Extrahiert den Operator-Namen für einen Gepäck-Durchlauf. """
    op_decisions = group[group['Klartext'].str.contains("Finale Operator-Entscheidung")]
    if not op_decisions.empty:
        last_decision_text = op_decisions.iloc[-1]['Klartext']
        match = re.search(r"von '([^']+)'", last_decision_text)
        if match:
            return match.group(1)
    return "N/A" # Wenn keine Operator-Entscheidung gefunden wurde

def consolidate_journeys(df):
    """ **NEU:** Fügt die Operator-Spalte zur Zusammenfassung hinzu. """
    if df.empty: return pd.DataFrame()
    linked_df = link_iata_to_oms(df)
    valid_bags = linked_df[linked_df['BagID'] != "N/A"].copy()
    if valid_bags.empty: return pd.DataFrame(columns=['Timestamp', 'BagID', 'IATA', 'End-Status', 'Operator'])
    
    grouped = valid_bags.groupby('BagID')
    summary_list = []
    for bag_id, group in grouped:
        summary_list.append({
            'Timestamp': group['Timestamp'].min(), 
            'BagID': bag_id,
            'IATA': get_correct_iata(group['IATA']),
            'End-Status': get_final_disposition(group),
            'Operator': get_operator(group) # Neue Spalte wird hier befüllt
        })
        
    summary = pd.DataFrame(summary_list)
    if summary.empty: return pd.DataFrame(columns=['Timestamp', 'BagID', 'IATA', 'End-Status', 'Operator'])
    
    # Stelle sicher, dass die Spalten in der gewünschten Reihenfolge sind
    return summary[['Timestamp', 'BagID', 'IATA', 'End-Status', 'Operator']].sort_values(by="Timestamp").reset_index(drop=True)