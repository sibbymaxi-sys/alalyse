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
    op_decisions = group['Klartext'][group['Klartext'].str.contains("Operator.*speichert finale Entscheidung")]
    if not op_decisions.empty:
        last_decision = op_decisions.iloc[-1]
        if "CLEAR" in last_decision: return "Freigegeben (Operator)"
        elif "ALARM" in last_decision: return "Alarm (Operator)"
    machine_decisions = group['Klartext'][group['Klartext'].str.contains("Maschinelle.*(?:LTR|EDS)", regex=True)]
    if not machine_decisions.empty:
        if "ALARM" in machine_decisions.iloc[-1]: return "Alarm (Maschine)"
        else: return "Freigegeben (Maschine)"
    return "Unbekannt"

def calculate_kpis(raw_df, journeys_df, start_date=None, end_date=None):
    """Berechnet alle wichtigen KPIs aus den Roh- und zusammengefassten Daten."""
    if journeys_df.empty or raw_df.empty: return {}

    # Filter DataFrames based on the date range
    if start_date and end_date:
        journeys_df = journeys_df[(journeys_df['Timestamp'] >= start_date) & (journeys_df['Timestamp'] <= end_date)]
        raw_df = raw_df[(raw_df['Timestamp'] >= start_date) & (raw_df['Timestamp'] <= end_date)]

    if journeys_df.empty or raw_df.empty: return {}

    # KPI 1: No-Read-Rate
    no_read_count = len(journeys_df[journeys_df['IATA'] == 'NO_READ'])
    nrr = (no_read_count / len(journeys_df)) * 100 if len(journeys_df) > 0 else 0

    # KPI 2: Durchschnittliche Durchlaufzeit
    start_times = raw_df[raw_df['Klartext'].str.contains("angelegt")].groupby('BagID')['Timestamp'].min()
    end_times = raw_df[raw_df['Klartext'].str.contains("abgeschlossen")].groupby('BagID')['Timestamp'].max()
    durations = (end_times - start_times).dropna().dt.total_seconds()
    avg_throughput = durations.mean() if not durations.empty else 0

    # KPI 3: Durchschnittliche Entscheidungszeit pro Operator
    op_times = {}
    machine_alarms = raw_df[raw_df['Klartext'].str.contains("Automatischer Scan abgeschlossen: ALARM")]
    for _, alarm_row in machine_alarms.iterrows():
        bag_id, alarm_time = alarm_row['BagID'], alarm_row['Timestamp']
        op_decision = raw_df[(raw_df['BagID'] == bag_id) & (raw_df['Klartext'].str.contains("Operator.*speichert finale Entscheidung")) & (raw_df['Timestamp'] > alarm_time)]
        if not op_decision.empty:
            decision_row = op_decision.iloc[0]
            op_name_match = re.search(r"Operator '([^']+)'", decision_row['Klartext'])
            if op_name_match:
                op_name = op_name_match.group(1)
                decision_time = (decision_row['Timestamp'] - alarm_time).total_seconds()
                if op_name not in op_times: op_times[op_name] = []
                op_times[op_name].append(decision_time)
    avg_op_times = {op: sum(times)/len(times) for op, times in op_times.items()}

    # Operator-Entscheidungen extrahieren (Korrektur für UserWarning)
    operator_journeys = journeys_df[journeys_df['End-Status'].str.contains("(Operator)", regex=True)]
    op_stats = operator_journeys['End-Status'].value_counts()
    
    # NEU: Performance pro Tag
    daily_performance = journeys_df.set_index('Timestamp').groupby(pd.Grouper(freq='D')).apply(
        lambda g: pd.Series({
            'Anzahl Wannen': len(g),
            'No-Read-Rate (%)': (len(g[g['IATA'] == 'NO_READ']) / len(g) * 100) if len(g) > 0 else 0
        })
    ).reset_index()
    daily_performance['Timestamp'] = daily_performance['Timestamp'].dt.date

    return {
        "nrr": nrr,
        "avg_throughput": avg_throughput,
        "avg_op_times": avg_op_times,
        "operator_stats": op_stats,
        "throughput_per_hour": journeys_df.set_index('Timestamp').resample('h').size(),
        "daily_performance": daily_performance
    }

def consolidate_journeys(df):
    if df.empty: return pd.DataFrame()
    linked_df = link_iata_to_oms(df)
    valid_bags = linked_df[linked_df['BagID'] != "N/A"].copy()
    if valid_bags.empty: return pd.DataFrame(columns=['Timestamp', 'BagID', 'IATA', 'End-Status'])
    grouped = valid_bags.groupby('BagID')
    summary_list = []
    for bag_id, group in grouped:
        summary_list.append({
            'Timestamp': group['Timestamp'].min(), 'BagID': bag_id,
            'IATA': get_correct_iata(group['IATA']),
            'End-Status': get_final_disposition(group)
        })
    summary = pd.DataFrame(summary_list)
    if summary.empty: return pd.DataFrame(columns=['Timestamp', 'BagID', 'IATA', 'End-Status'])
    return summary.sort_values(by="Timestamp").reset_index(drop=True)