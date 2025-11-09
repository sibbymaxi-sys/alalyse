# oms_report_generator.py
print("--- [V13-Report] oms_report_generator.py wird geladen ... ---")

import pandas as pd
from datetime import datetime
import re
import pytz # Import für Zeitzonen

def generate_oms_report(df: pd.DataFrame, out_path: str):
    """
    Erzeugt pro IATA einen Klartextbericht mit erklärten Ereignissen.
    Basiert auf dem V13-Skript des Users.
    Nimmt ein BEREITS GEPARSTES DataFrame entgegen.
    """
    if df.empty:
        print("Keine OMS-Ereignisse für den Report gefunden – Abbruch.")
        return False

    try:
        # Daten sind bereits UTC, sortieren
        df = df.sort_values("Timestamp")
        total_iata = df["IATA"].nunique()
        
        # Für die Anzeige im Report nach Berlin-Zeit konvertieren
        local_tz = pytz.timezone('Europe/Berlin')
        df['Timestamp_Local'] = df['Timestamp'].dt.tz_convert(local_tz)

        with open(out_path, "w", encoding="utf-8") as rep:
            rep.write(f"OMS-Analyser V13 – Bericht erstellt am {datetime.now()}\n")
            rep.write(f"Insgesamt {total_iata} IATA-Codes gefunden.\n")
            rep.write("═" * 90 + "\n\n")

            for iata, group in df.groupby("IATA"):
                rep.write(f"IATA {iata} – {len(group)} Ereignisse\n")
                rep.write("─" * 90 + "\n")

                # Zähle die Ereignisse (basierend auf der Klartext-Logik von V13)
                alerts = sum("ALARM" in str(x).upper() for x in group["Klartext"])
                clears = sum("CLEAR" in str(x).upper() for x in group["Klartext"])
                diverter = sum("Weiche" in str(x) or "diverter" in str(x).lower() for x in group["Klartext"])
                operator = sum("Operator" in str(x) or "Bedien" in str(x) for x in group["Klartext"])

                for _, row in group.iterrows():
                    ts_str = row["Timestamp_Local"].strftime("%Y-%m-%d %H:%M:%S")
                    klar = row["Klartext"]
                    rep.write(f"  • {ts_str} → {klar}\n")

                rep.write("\nZusammenfassung (automatisch interpretiert):\n")
                rep.write(f"  – {alerts} × Alarmmeldungen (Bags mit Sicherheitsprüfung)\n")
                rep.write(f"  – {clears} × Freigaben / Clear-Signale\n")
                rep.write(f"  – {diverter} × Weichen-/Umlenk-Aktionen\n")
                rep.write(f"  – {operator} × Manuelle Operator-Entscheidungen\n")
                rep.write("\n\n")

        print(f"Bericht gespeichert unter {out_path}")
        return True
        
    except Exception as e:
        print(f"--- FEHLER bei generate_oms_report: {e} ---")
        traceback.print_exc()
        return False