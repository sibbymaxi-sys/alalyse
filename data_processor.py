# data_processor.py
print("--- [V19-FIX-User] data_processor.py wird geladen (JourneyID an OMS-Tab übergeben) ... ---")

import pandas as pd
import re
import traceback
from datetime import timedelta # Import für PLC-Logik

# --- Spalten-Definitionen (Unverändert) ---
FINAL_JOURNEY_COLS_SCANNER = ['Timestamp', 'BagID', 'IATA', 'Machine', 'EDS', 'Operator', 'Final', 'OperatorName']
# --- KORREKTUR (V19): JourneyID hinzugefügt ---
FINAL_JOURNEY_COLS_OMS = ['Timestamp', 'IATA', 'EDS', 'Operator', 'Final', 'JourneyID']


# --- Extraktions-Logik (Unverändert) ---
def _extract_decisions(df_group):
    """Extrahiert Entscheidungen aus einer gruppierten Klartext-Liste."""
    
    klartext_str = ' '.join(df_group['KlartextList'])
    
    # 1. EDS (Maschinentscheidung)
    eds_decision = "N/A"
    if "Maschinelle Entscheidung (EDS): **ALARM**" in klartext_str:
        eds_decision = "ALARM"
    elif "Maschinelle Entscheidung (EDS): **CLEAR**" in klartext_str:
        eds_decision = "CLEAR"
    elif "Maschinelle Entscheidung (LTR): **ALARM**" in klartext_str: # Fallback LTR
        eds_decision = "ALARM"
    elif "Maschinelle Entscheidung (LTR): **CLEAR**" in klartext_str: # Fallback LTR
        eds_decision = "CLEAR"
        
    # 2. Operator (V16/V15 Logik: Priorisiert Op 3/4)
    operator_decision = "N/A"
    operator_name = "N/A"
    
    op_match_priority = list(re.finditer(r"Operator-Entscheidung von '(operator3|operator4)': \*\*(CLEAR|ALARM)\*\*", klartext_str))
    
    if op_match_priority:
        last_match = op_match_priority[-1]
        operator_name = last_match.group(1)
        operator_decision = last_match.group(2)
    else:
        op_match_fallback = list(re.finditer(r"Operator-Entscheidung von '([^']+)': \*\*(CLEAR|ALARM)\*\*", klartext_str))
        if op_match_fallback:
            last_match = op_match_fallback[-1]
            operator_name = last_match.group(1)
            operator_decision = last_match.group(2)
        
    # 3. Final (OMS-Befehl)
    final_decision = "N/A"
    if "Finaler Befehl an Förderanlage gesendet: **Alarm (ALARM)**" in klartext_str:
        final_decision = "ALARM"
    elif "Finaler Befehl an Förderanlage gesendet: **Freigabe (CLEAR)**" in klartext_str:
        final_decision = "CLEAR"
        
    # 4. Fallback-Logik für 'Final' (Regel: Nur Op 3/4)
    if final_decision == 'N/A':
        if operator_name in ['operator3', 'operator4']:
            final_decision = operator_decision
            
    return eds_decision, operator_decision, operator_name, final_decision
# --- Ende Extraktions-Logik ---


# --- SCANNER-ANALYSE (Tab 1) - UNVERÄNDERT (V15) ---
def consolidate_scanner_journeys(raw_df):
    """
    (V15) Konsolidiert NUR Scanner-Logs.
    Führt IATA-Propagation VOR der Gruppierung durch.
    """
    if raw_df.empty:
        return pd.DataFrame(columns=FINAL_JOURNEY_COLS_SCANNER), raw_df

    # (V15: IATA-Propagation)
    raw_df['BagID'] = raw_df['BagID'].replace('N/A', pd.NA)
    raw_df = raw_df[raw_df['BagID'].notna()].copy()
    raw_df['IATA'] = raw_df['IATA'].replace('N/A', pd.NA)
    if raw_df.empty:
        return pd.DataFrame(columns=FINAL_JOURNEY_COLS_SCANNER), raw_df
    raw_df.sort_values(by=['BagID', 'Timestamp'], inplace=True)
    try:
        raw_df['IATA'] = raw_df.groupby('BagID')['IATA'].transform(lambda x: x.ffill().bfill())
    except Exception as e:
        print(f"--- FEHLER bei IATA-Propagation (V15): {e} ---")
        traceback.print_exc()

    def set_no_read(row):
        if row['IATA'] is pd.NA:
            return 'NO_READ'
        return row['IATA']
    raw_df['IATA'] = raw_df.apply(set_no_read, axis=1)
    raw_df = raw_df.fillna('N/A') 

    grouping_keys = ['BagID', 'IATA']
    raw_df = raw_df[~((raw_df['BagID'] == 'N/A') & (raw_df['IATA'] == 'N/A'))].copy()

    if raw_df.empty:
        return pd.DataFrame(columns=FINAL_JOURNEY_COLS_SCANNER), raw_df

    raw_df.sort_values(by=grouping_keys + ['Timestamp'], inplace=True)

    try:
        journeys = raw_df.groupby(grouping_keys).agg(
            Timestamp=('Timestamp', 'first'),
            Machine=('Device', lambda x: x[x != 'N/A'].iloc[0] if not x[x != 'N/A'].empty else 'N/A'),
            KlartextList=('Klartext', list)
        ).reset_index() 

        decisions = journeys.apply(_extract_decisions, axis=1, result_type='expand')
        journeys['EDS'] = decisions[0]
        journeys['Operator'] = decisions[1]
        journeys['OperatorName'] = decisions[2]
        journeys['Final'] = decisions[3]

        return journeys[FINAL_JOURNEY_COLS_SCANNER].sort_values(by="Timestamp"), raw_df

    except Exception as e:
        print(f"--- FEHLER bei consolidate_scanner_journeys: {e} ---")
        traceback.print_exc()
        return pd.DataFrame(columns=FINAL_JOURNEY_COLS_SCANNER), raw_df
# --- ENDE SCANNER-ANALYSE ---


# --- OMS-ANALYSE (Tab 4) - KORRIGIERT (V19) ---
def consolidate_oms_journeys(raw_df):
    """
    NEU (V13): Konsolidiert NUR OMS-Logs.
    KORRIGIERT (V18): Wendet die 5-Minuten-Trennungsregel an.
    """
    if raw_df.empty:
        return pd.DataFrame(columns=FINAL_JOURNEY_COLS_OMS), raw_df

    raw_df['IATA'] = raw_df['IATA'].replace('N/A', pd.NA)
    raw_df = raw_df[raw_df['IATA'].notna()].copy() 

    if raw_df.empty:
        return pd.DataFrame(columns=FINAL_JOURNEY_COLS_OMS), raw_df

    # --- START KORREKTUR (V18): 5-Minuten-Regel für OMS ---
    
    raw_df.sort_values(by=['IATA', 'Timestamp'], inplace=True)
    raw_df['TimeDiff'] = raw_df.groupby('IATA')['Timestamp'].diff()
    raw_df['IATADiff'] = (raw_df['IATA'] != raw_df['IATA'].shift())
    
    time_threshold = timedelta(minutes=5)
    
    is_new_journey = (
        (raw_df['TimeDiff'] > time_threshold) |
        (raw_df['IATADiff'] == True)
    )
    
    raw_df['JourneyID'] = is_new_journey.cumsum()
    # --- ENDE KORREKTUR (V18) ---

    print(f"--- DEBUG (consolidate_oms_journeys V18): {raw_df['JourneyID'].nunique()} OMS-Journeys (5-Min-Regel) identifiziert.")

    try:
        # Gruppiere nach der neuen JourneyID
        journeys = raw_df.groupby('JourneyID').agg(
            Timestamp=('Timestamp', 'first'),
            IATA=('IATA', 'first'), 
            KlartextList=('Klartext', list)
        ).reset_index() # V19: Behält JourneyID

        # Wende die Entscheidungslogik an
        decisions = journeys.apply(_extract_decisions, axis=1, result_type='expand')
        journeys['EDS'] = decisions[0]
        journeys['Operator'] = decisions[1]
        journeys['Final'] = decisions[3] 

        return journeys[FINAL_JOURNEY_COLS_OMS].sort_values(by="Timestamp"), raw_df

    except Exception as e:
        print(f"--- FEHLER bei consolidate_oms_journeys: {e} ---")
        traceback.print_exc()
        return pd.DataFrame(columns=FINAL_JOURNEY_COLS_OMS), raw_df
# --- ENDE OMS-ANALYSE ---


# =============================================================================
# --- START: SPS-LOGIK (V17 - KORRIGIERT mit 5-Minuten-Regel) ---
# =============================================================================

def _find_decision_plc(text_list): # (Umbenannt, um Konflikt zu vermeiden)
    """Sucht in einer Liste von Klartext-Einträgen nach der finalen Entscheidung."""
    for text in reversed(text_list): 
        if "FEHLER:" in text:
            return "ERROR"
        match = re.search(r"Entscheidung vom Scanner empfangen: Decision \d \((CLEAR|REJECT)\)", text)
        if match:
            return match.group(1)
    return "N/A"

def _find_first_step_plc(text_list): # (Umbenannt)
    """Sucht den ersten Schritt (normalerweise 'Plausibilitätsprüfung')."""
    for text in text_list:
        if "Plausibilitätsprüfung" in text:
            return text
    return text_list[0] if text_list else "N/A"


def consolidate_plc_journeys(raw_plc_df):
    """
    Fasst rohe SPS-Log-Einträge zu "Journeys" zusammen.
    KORRIGIERT (V17): 5-Minuten-Regel
    """
    
    if raw_plc_df.empty:
        print("--- DEBUG (consolidate_plc_journeys): Leeres DataFrame übergeben.")
        return pd.DataFrame(), raw_plc_df

    raw_plc_df = raw_plc_df.sort_values(by=['IATA', 'Timestamp']).reset_index(drop=True)

    raw_plc_df['TimeDiff'] = raw_plc_df.groupby('IATA')['Timestamp'].diff()
    raw_plc_df['IATADiff'] = (raw_plc_df['IATA'] != raw_plc_df['IATA'].shift())
    
    time_threshold = timedelta(minutes=5) # V17-Regel
    
    is_new_journey = (
        (raw_plc_df['TimeDiff'] > time_threshold) |
        (raw_plc_df['IATADiff'] == True) |
        (raw_plc_df['Klartext'].str.contains("FEHLER:", na=False))
    )
    
    raw_plc_df['JourneyID'] = is_new_journey.cumsum()

    print(f"--- DEBUG (consolidate_plc_journeys V17): {raw_plc_df['JourneyID'].nunique()} SPS-Journeys (5-Min-Regel) identifiziert.")

    try:
        summary_df = raw_plc_df.groupby('JourneyID').agg(
            Timestamp=('Timestamp', 'first'),
            IATA=('IATA', 'first'),
            _KlartextList=('Klartext', list)
        ).reset_index() 
        
        summary_df['Decision'] = summary_df['_KlartextList'].apply(_find_decision_plc)
        summary_df['Klartext'] = summary_df['_KlartextList'].apply(_find_first_step_plc)
        summary_df = summary_df.drop(columns=['_KlartextList'])
        summary_df = summary_df.sort_values(by="Timestamp").reset_index(drop=True)

        print(f"--- DEBUG (consolidate_plc_journeys): Zusammenfassung mit {len(summary_df)} Zeilen erstellt.")
        
        return summary_df, raw_plc_df
        
    except Exception as e:
        print(f"--- FEHLER bei consolidate_plc_journeys: {e} ---")
        traceback.print_exc()
        return pd.DataFrame(), raw_plc_df

# =============================================================================
# --- ENDE: SPS-LOGIK ---
# =============================================================================