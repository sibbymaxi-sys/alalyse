# mv3d_error_definitions.py (Version 3.0 - MASTER)
# Kombiniert die originale User-Datei mit den neuen
# Regeln aus den diagserv/optinet-Snippets.
import re

# Das Format ist:
# r"Ein Regex-Muster, das den Fehler im Log findet": {
#     "cause": "Eine mögliche Ursache für diesen Fehler.",
#     "action": "Ein Lösungsvorschlag oder eine Handlungsanweisung."
# }
# (.*) fängt variable Teile ein, {0}, {1} etc. fügen sie in den Text ein.

ERROR_DEFINITIONS = {
    
    # --- SCS/BMS Faults (mfc= / fault_cause=) (Aus deiner Datei) ---
    r"mfc=([1-9]\d*)" : { 
        "cause": "SCS meldet Hauptfehlerursache (mfc) = {0}. Siehe SCS Fault Code Liste.",
        "action": "Prüfen Sie die SCS Fault Code Liste für FC {0}. Suchen Sie nach spezifischeren Fehlermeldungen im scs.log oder anderen Logs."
    },
    r"fault_cause = ([1-9]\d*)": { 
        "cause": "BMS meldet Fehlerursache (fault_cause) = {0}. Siehe SCS Fault Code Liste.",
        "action": "Prüfen Sie die SCS Fault Code Liste für FC {0}. Suchen Sie nach spezifischeren Fehlermeldungen im bms.log oder anderen Logs."
    },
     r"KEYPOWEROFF|\(FC 3\)": { 
        "cause": "Der Hauptschalter (Key Power) ist ausgeschaltet (FC 3).",
        "action": "Schalten Sie das System mit dem Schlüssel ein."
    },
    r"SDB2_FAULT|\(FC 4\)": {
        "cause": "Fehler im System Distribution Board 2 (SDB2) (FC 4).",
        "action": "Überprüfen Sie SDB2-Verbindungen und Status-LEDs. Evtl. Austausch nötig."
    },
    r"BIT_FAULT|\(FC 5\)": {
        "cause": "Fehler während des Built-In Tests (BIT) (FC 5).",
        "action": "Überprüfen Sie die diag/bit Logs für spezifische Fehlerdetails."
    },
    r"DIAG_FAULT|\(FC 6\)": {
        "cause": "Ein Diagnose-Fehler ist aufgetreten (FC 6).",
        "action": "Überprüfen Sie die Diagnose-Logs."
    },
    r"DIAG_POST_TIMEOUT|\(FC 7\)": {
        "cause": "Zeitüberschreitung während des Power-On Self Tests (POST) der Diagnose (FC 7).",
        "action": "Mögliches Hardware-Problem. Neustart versuchen, ansonsten Service kontaktieren."
    },
    r"SRC_FAILED|\(FC 8\)": {
        "cause": "Fehler bei der Software-Registrierung oder -Komponente (SRC) (FC 8).",
        "action": "Systemneustart. Bei Wiederholung Software-Problem untersuchen."
    },
    r"ISHWFAULTCONDITION|\(FC 9\)": {
        "cause": "Ein allgemeiner Hardwarefehler wurde gemeldet (FC 9). Der Ursprung ist in anderen Fehlercodes zu finden.",
        "action": "WICHTIG: Filtern Sie das bms.log oder scs.log nach 'Fault cause'/'mfc=' und suchen Sie den Fehlercode *vor* FC 9, um die eigentliche Ursache zu finden."
    },
    r"SUBSYSTEMMISSING|\(FC 11\)": {
        "cause": "Ein benötigtes Subsystem ist nicht verfügbar oder antwortet nicht (FC 11).",
        "action": "Überprüfen Sie Verbindungen und Status der Subsysteme (BMS, IAC, DPP, DIAGS - siehe FC 47-50)."
    },
    r"DCBOFFSET_FAILURE|\(FC 13\)": {
        "cause": "Fehler bei der DCB (Detector Control Board) Offset-Kalibrierung (FC 13).",
        "action": "Offset-Kalibrierung erneut durchführen. Bei Wiederholung DCB oder Detektoren prüfen."
    },
    r"ESTOP|\(FC 16\)": {
        "cause": "Not-Halt (E-Stop) wurde ausgelöst (FC 16).",
        "action": "Not-Halt entriegeln und System zurücksetzen."
    },
    r"ILOCK|\(FC 17\)": {
        "cause": "Interlock-Fehler (Sicherheitskreis unterbrochen, z.B. Tür, Panel) (FC 17).",
        "action": "Alle Sicherheitskontakte und Türen prüfen und schließen."
    },
    r"WATCHDOG|\(FC 21\)": {
        "cause": "System-Watchdog-Fehler (Zeitüberwachung) (FC 21).",
        "action": "Mögliches Software- oder Hardwareproblem. Systemneustart. Bei Wiederholung Service kontaktieren."
    },
    r"SYSTIC_FAULT|\(FC 22\)": {
        "cause": "Fehler auf dem SYSTIC Board (Timing und Kontrolle) (FC 22).",
        "action": "Überprüfen Sie SYSTIC Board, Verbindungen und Stromversorgung. Evtl. Austausch nötig."
    },
    r"ENCODER_FAULT|\(FC 23\)": {
        "cause": "Fehler am Encoder (Positionsgeber Förderband) (FC 23).",
        "action": "Encoder prüfen (Verschmutzung, Kabel, Ausrichtung). Evtl. Austausch nötig."
    },
    r"LIGHT_CURTAIN_FAULT|\(FC 24\)": {
        "cause": "Fehler an der Lichtschranke (FC 24).",
        "action": "Lichtschranke prüfen (Verschmutzung, Ausrichtung, Kabel)."
    },
    r"GALIL_FAULT|\(FC 25\)": {
        "cause": "Fehler an der Galil-Motorsteuerung (falls verwendet) (FC 25).",
        "action": "Überprüfen Sie die Galil-Steuerung und angeschlossene Motoren/Komponenten."
    },
    r"ACUVIM_FAULT|\(FC 26\)": {
        "cause": "Fehler am Acuvim-Energiemessgerät (FC 26).",
        "action": "Überprüfen Sie das Acuvim-Gerät und seine Kommunikation."
    },
    r"YASKAWA_FAULT|\(FC 27\)": {
        "cause": "Fehler am Yaskawa-Antrieb/Motorsteuerung (FC 27).",
        "action": "Überprüfen Sie den Yaskawa-Antrieb auf Fehlercodes und Status."
    },
    r"MFORCE_FAULT|\(FC 28\)": {
        "cause": "Fehler an der MForce-Steuerung (FC 28).",
        "action": "Überprüfen Sie die MForce-Steuerung und angeschlossene Komponenten."
    },
    r"UPS_FAULT|\(FC 29\)": {
        "cause": "Fehler an der unterbrechungsfreien Stromversorgung (USV/UPS) (FC 29).",
        "action": "Überprüfen Sie den UPS-Status (Batterie, Last, Fehleranzeigen)."
    },
    r"HVPS_FAULT|\(FC 30\)": {
        "cause": "Fehler am Hochspannungsnetzteil (HVPS) (FC 30). Mögliche Ursachen: Arc errors, XRT failure, HVPS failure, Control or safety circuit failure.",
        "action": "Nutzen Sie das HVPS-Monitor-Tool im Diagnosemodus. Rampen Sie kV/mA hoch und beobachten Sie Fehler. Prüfen Sie Trace.log auf 'fault flags' (HV-reg, HV_rail, Aux_ps) und 'Arc count'."
    },
    r"DCB_FAULT|\(FC 31\)": {
        "cause": "Fehler am Detector Control Board (DCB) (FC 31). Mögliche Ursachen: Zu viele 'bad detectors', defektes FPGA, defektes Detektormodul, Kabelprobleme, Komponentenausfall.",
        "action": "Prüfen Sie /opt/eds/etc/bad_detectors.dat. Prüfen Sie Kabelverbindungen. Nutzen Sie das ADD-Plot-Tool zur Datenanalyse. Evtl. DCB JU1/J2 Jumper entfernen. Siehe Troubleshooting Abschnitt 1 für DCB errors."
    },
    r"SYSTEM_VERIFY_FAULT|\(FC 32\)": {
        "cause": "Fehler während der Systemverifizierung (FC 32).",
        "action": "Überprüfen Sie die Logs auf spezifische Fehler während des Verifizierungsprozesses."
    },
    r"BMS_ENTRANCE_BAG_JAM|\(FC 33\)": {
        "cause": "Taschenstau am Eingang (BMS Entrance) (FC 33).",
        "action": "Entfernen Sie die Blockade am Systemeingang. Prüfen Sie die Lichtschranken."
    },
    r"BMS_BHS_FAULT|\(FC 34\)": {
        "cause": "Fehler vom Baggage Handling System (BHS) an das BMS gemeldet (FC 34).",
        "action": "Überprüfen Sie den Status und die Fehlermeldungen des BHS."
    },
    r"SYSTIC_TIMEOUT|\(FC 35\)": {
        "cause": "Zeitüberschreitung bei der Kommunikation mit dem SYSTIC Board (FC 35).",
        "action": "Überprüfen Sie die Netzwerkverbindung zum SYSTIC Board."
    },
    r"SDB2_TIMEOUT|\(FC 36\)": {
        "cause": "Zeitüberschreitung bei der Kommunikation mit SDB2 (FC 36).",
        "action": "Überprüfen Sie die Netzwerkverbindung zu SDB2."
    },
    r"DCB_TIMEOUT|\(FC 37\)": {
        "cause": "Zeitüberschreitung bei der Kommunikation mit einem DCB (FC 37).",
        "action": "Überprüfen Sie die Verbindungen zu den DCBs."
    },
    r"DPP_RTR_DOWN|\(FC 38\)": {
        "cause": "DPP (Data PreProcessor) Rechner ist nicht bereit (RTR Down) (FC 38). Mögliche Ursachen: Zu viele Taschen in der Recon-Warteschlange, Rekonstruktionsfehler, Bildartefakte, defekte IRC.",
        "action": "Überprüfen Sie den Status des DPP-Rechners (Netzwerk, Auslastung, Logs). Prüfen Sie die Bildrekonstruktion (DPP.log, DCS.log). Siehe Troubleshooting Abschnitt 3."
    },
    r"BMS_RTR_DOWN|\(FC 39\)": {
        "cause": "BMS (Baggage Management System) Rechner ist nicht bereit (RTR Down) (FC 39).",
        "action": "Überprüfen Sie den Status des BMS-Rechners (Netzwerk, Auslastung, Logs)."
    },
    r"IAC_RTR_DOWN|\(FC 40\)": {
        "cause": "IAC (Image Analysis Computer) Rechner ist nicht bereit (RTR Down) (FC 40). Mögliche Ursachen: Zu viele Taschen in der Level-2-Warteschlange, zu viele BNAs (Algorithm/Reconstruction errors).",
        "action": "Überprüfen Sie den Status des IAC-Rechners (Netzwerk, Auslastung, Logs). Prüfen Sie Algorithmus- und Rekonstruktions-Logs (DPP.log, IAC Logs). Siehe Troubleshooting Abschnitt 4."
    },
    r"DPP_OPTSTATE_FAULT|\(FC 41\)": {
        "cause": "Fehler im Betriebszustand (Operational State) des DPP (FC 41).",
        "action": "Überprüfen Sie die DPP-Logs für spezifische Fehlerdetails."
    },
    r"IAC_OPTSTATE_FAULT|\(FC 42\)": {
        "cause": "Fehler im Betriebszustand (Operational State) des IAC (FC 42).",
        "action": "Überprüfen Sie die IAC-Logs für spezifische Fehlerdetails."
    },
    r"INIT_TIMEOUT_FAULT|\(FC 43\)": {
        "cause": "Zeitüberschreitung während der Systeminitialisierung (FC 43). Mögliche Ursachen: Fehler beim Initialisieren, ein Rechner bootet nicht, andere Hardwarefehler.",
        "action": "Systemneustart versuchen. Über KVM prüfen, ob alle Rechner bis zum Login booten. SSH-Verbindung zu jedem Rechner testen. scs.log oder diag/bit log prüfen. Siehe Troubleshooting Abschnitt 5."
    },
    r"SEASONING_FAILED|\(FC 44\)": {
        "cause": "Fehler während des Tube Seasoning (Konditionierung der Röntgenröhren) (FC 44).",
        "action": "Seasoning-Prozess erneut starten. HVPS und Röntgenröhren prüfen. Trace.log prüfen."
    },
    r"TRANSIENTS_FAILED|\(FC 45\)": {
        "cause": "Fehler bei der Transienten-Messung/Kalibrierung (FC 45).",
        "action": "Kalibrierung erneut durchführen. Detektoren und HVPS prüfen."
    },
    r"ARRAYTESTS_FAILED|\(FC 46\)": {
        "cause": "Fehler bei den Detektor-Array-Tests (FC 46).",
        "action": "Betroffenes Array identifizieren (Logs, DCS.log). Detektoren, Quad-Boards, Combiner-Boards und HCB prüfen."
    },
    r"BMS_SUBSYS_MISSING|\(FC 47\)": {
        "cause": "Das BMS Subsystem fehlt oder antwortet nicht (FC 47).",
        "action": "Überprüfen Sie den BMS-Rechner und die Netzwerkverbindung."
    },
    r"IAC_SUBSYS_MISSING|\(FC 48\)": {
        "cause": "Das IAC Subsystem fehlt oder antwortet nicht (FC 48).",
        "action": "Überprüfen Sie den IAC-Rechner und die Netzwerkverbindung."
    },
    r"DPP_SUBSYS_MISSING|\(FC 49\)": {
        "cause": "Das DPP Subsystem fehlt oder antwortet nicht (FC 49).",
        "action": "Überprüfen Sie den DPP-Rechner und die Netzwerkverbindung."
    },
    r"DIAGS_SUBSYS_MISSING|\(FC 50\)": {
        "cause": "Das Diagnose Subsystem fehlt oder antwortet nicht (FC 50).",
        "action": "Überprüfen Sie den Diagnose-Rechner/Komponente und die Netzwerkverbindung."
    },
    r"PLC_CONNECTION_LOSS|\(FC 51\)": {
        "cause": "Verbindung zur SPS (PLC) verloren (FC 51).",
        "action": "Überprüfen Sie die Netzwerkverbindung (Kabel, IP-Einstellungen) zwischen MV3D-PLC und BHS-PLC."
    },
    r"DPP_HIGH_WATERMARK|\(FC 52\)": {
        "cause": "Hoher Wasserstand (High Watermark) im DPP erreicht (zu viele Daten/Bilder in der Warteschlange) (FC 52).",
        "action": "Überprüfen Sie die Auslastung des DPP. Möglicherweise Performance-Problem oder nachgelagerter Stau (IAC)."
    },
    r"LIGHTCURTAIN_CHANGED|\(FC 53\)": {
        "cause": "Status der Lichtschranke hat sich geändert (möglicherweise unterbrochen) (FC 53).",
        "action": "Prüfen Sie, ob die Lichtschranke frei ist. Ggf. auf Defekt prüfen."
    },
    r"CHILLER_FAULT|\(FC 54\)": {
        "cause": "Fehler am Kühlsystem (Chiller) (FC 54).",
        "action": "Überprüfen Sie den Chiller auf Fehleranzeigen, Füllstand, Pumpen."
    },
    r"SYSTEMP_(AMBIENT|INLET_BOX|OUTLET_BOX|SARCOPHAGUS|COMPUTER_RACK|ENCODER_MONITOR)|\(FC (5[5-9]|60)\)": {
        "cause": "Temperaturwarnung/-fehler im Bereich '{0}' (FC {1}).",
        "action": "Überprüfen Sie die Kühlung/Lüftung des Bereichs '{0}' und die Umgebungstemperatur."
    },

    # --- FSM Log Errors (Aus deiner Datei) ---
    r"limitSwitchWarning=1": {
        "cause": "Warnung (FSM Log): Endschalter für Bandlauf (Belt Tracking) wurde erreicht.",
        "action": "Überprüfen Sie den Bandlauf (Belt Tracking) und justieren Sie ihn gemäß Anleitung."
    },
    r"limitSwitchFault=1": {
        "cause": "Fehler (FSM Log): Endschalter für Bandlauf (Belt Tracking) wurde ausgelöst (kritisch).",
        "action": "System stoppt. Überprüfen Sie sofort den Bandlauf und die Mechanik. Justieren/Reparieren Sie den Bandlauf."
    },

    # --- PLC Log Errors (Aus deiner Datei) ---
    r"\[plc.*?\].*bag jam": {
        "cause": "Taschenstau (Bag Jam) im PLC-Log gemeldet.",
        "action": "Überprüfen Sie das PLC.log auf die genaue Position (IPEC, XPEC, interne PECs?). Beseitigen Sie die Blockade."
    },
    r"XBDP.*?TD: (8)": {
        "cause": "Tracking Decision 8 (PLC Log): Eingang Misstrack.",
        "action": "Tasche wurde am Eingang verloren. Überprüfen Sie Eingangskulissen, PECs, BHS-Übergabe."
    },
    r"XBDP.*?TD: (9)": {
        "cause": "Tracking Decision 9 (PLC Log): Ausgang Misstrack.",
        "action": "Tasche wurde am Ausgang verloren. Überprüfen Sie Ausgangskulissen, PECs, BHS-Übergabe."
    },
     r"XBDP.*?TD: (6)": {
        "cause": "Tracking Decision 6 (PLC Log): Taschenabstandsfehler (Bag Spacing Error).",
        "action": "Zwei Taschen wurden zu dicht aufeinander erkannt. Überprüfen Sie die BHS-Zuführung auf korrekten Abstand."
    },
     r"tracking pec.*error|fault": {
       "cause": "Fehler im Zusammenhang mit einem Tracking PEC gemeldet (PLC Log).",
       "action": "Überprüfen Sie das PLC.log auf Details. Prüfen Sie die betroffene Lichtschranke (Verschmutzung, Ausrichtung, Kabel)."
     },
     r"Miss Bags S1: (\d+) S2: (\d+) S3: (\d+)": {
        "cause": "PLC Log: Misstrack Zählerstände - S1 (Eingang): {0}, S2 (Scan): {1}, S3 (Ausgang): {2}.",
        "action": "Hohe Zahlen in S1/S3 deuten auf Probleme mit Kulissen/Übergabe hin. S2 ist selten. Beobachten Sie die Entwicklung der Zähler."
     },

    # --- BHS / Scanner Bag Log Errors (Aus deiner Datei) ---
    r"exceptions = 2": {
        "cause": "BNA (Bag Not Analyzed) aufgrund von Hardware-/Verbindungsproblemen (Scanner Bag Log: Exception 2).",
        "action": "Überprüfen Sie Netzwerk- und Hardwareverbindungen im Datenpfad (Detektoren -> HCB -> DPP -> IAC)."
    },
    r"exceptions = 32": {
        "cause": "BNA (Bag Not Analyzed) aufgrund von Datenintegritätsproblemen (Scanner Bag Log: Exception 32).",
        "action": "Überprüfen Sie DPP/DCS Logs auf 'filler' oder andere Datenfehler. Prüfen Sie Detektor-Kalibrierung/Gesundheit."
    },
    r"exceptions = 48": {
        "cause": "BNA (Bag Not Analyzed) aufgrund einer Kombination von Hardware- und Datenproblemen (Scanner Bag Log: Exception 48).",
        "action": "Überprüfen Sie sowohl Verbindungen als auch Datenqualität (siehe Exception 2 und 32)."
    },
    r"no 2a operator =1": {
        "cause": "Kein Level 2a Operator war zum Zeitpunkt der Entscheidung eingeloggt (BHS Log).",
        "action": "Stellen Sie sicher, dass genügend Level 2a Operatoren an den View Stations eingeloggt sind."
    },
    r"no 2b operator =1": {
        "cause": "Kein Level 2b Operator war zum Zeitpunkt der Entscheidung eingeloggt (BHS Log).",
        "action": "Stellen Sie sicher, dass genügend Level 2b Operatoren an den View Stations eingeloggt sind."
    },

    # --- DCS/DPP/Trace Log Errors (Aus deiner Datei) ---
    r"fault flags .* HV-reg": {
       "cause": "Trace Log: HVPS 'HV-reg' Fehler - Generischer Fehler, oft Röhren-Arcing oder Filamentkabel.",
       "action": "System aus, 10min warten! HV-Verbindungen prüfen/reinigen/neu fetten. Gasket prüfen. HVPS-Diagnose durchführen."
    },
    r"fault flags .* HV_rail": {
       "cause": "Trace Log: HVPS 'HV_rail' Fehler - Problem mit der HVPS-Eingangsspannung.",
       "action": "Überprüfen Sie die Stromversorgung des HVPS und die Eingangsverbindungen."
    },
    r"fault flags .* Aux_ps": {
       "cause": "Trace Log: HVPS 'Aux_ps' Fehler - Internes Hilfsnetzteil des HVPS ausgefallen.",
       "action": "HVPS muss ersetzt werden."
    },
    r"FAILURES DETECTED during HVPS self test": {
         "cause": "Trace Log: Fehler während des HVPS Selbsttests.",
         "action": "Überprüfen Sie die spezifischen Fehlermeldungen im Trace Log rund um diesen Eintrag. Führen Sie HVPS-Diagnose durch."
    },
    r"Arc count": { # Hinweis: Dies wird von der spezifischeren diagserv-Regel (unten) überschrieben, wenn sie zutrifft
         "cause": "Trace Log: Zähler für Lichtbögen (Arcs) in HVPS/Röhre wird erwähnt.",
         "action": "Hohe oder steigende 'Arc counts' deuten auf Probleme mit HV-Verbindungen, Gasket oder Röhre hin. Siehe 'Tube Arcing'."
    },
    r"\[dcs.*?].*filler": {
        "cause": "DCS/DPP Log: 'filler' Daten deuten auf unvollständige oder fehlerhafte Detektordaten hin.",
        "action": "Prüfen Sie Detektorstatus (ADD plots), DCB/HCB-Verbindungen, Ausrichtung, HV-Stabilität."
    },
    r"no barker": {
        "cause": "DCS Log: 'no barker' - System hat Schwierigkeiten, den Start einer Tasche zu erkennen.",
        "action": "Überprüfen Sie Encoder-Signalqualität, Ausrichtung und SYSTIC-Board."
    },
    r"(HCB\d).* disconnected": {
        "cause": "DCS Log: HCB '{0}' hat die Verbindung verloren.",
        "action": "Überprüfen Sie Stromversorgung, Glasfaserverbindung zum DPP und Status-LEDs von HCB '{0}'."
    },
    r"Array (\d) disconnected": {
        "cause": "DCS Log: Detektor-Array {0} (0-6) hat die Verbindung verloren.",
        "action": "Überprüfen Sie 5V-Stromversorgung des Arrays, Flachbandkabel zum Combiner/HCB, HCB-Status."
    },
    r"max Y = (\d+)": {
       "cause": "DPP Log: Maximale Taschenhöhe {0} gemessen.",
       "action": "Wenn dieser Wert konstant >= 233 ist, reinigen Sie den Höhendetektor-Streifen."
    },
    r"Beginning reconstruction on IRC \d+ using cores: (\d+),(\d+) \(pair (\d+)\)": {
        "cause": "DPP Log: Rekonstruktion startet auf Cores {0},{1} (Paar {2}).",
        "action": "Normalerweise informativ. Wenn *immer nur dasselbe Paar* angezeigt wird (z.B. immer nur 1,2), könnte ein Problem mit dem DPP/IRC vorliegen."
    },
    r"session error.*sender": {
        "cause": "DPP Log: Session Error (Sender) - Problem bei der Datenübertragung vom DPP.",
        "action": "Überprüfen Sie DPP-Logs auf spezifische Kommunikationsfehler oder Verarbeitungsprobleme."
    },
    r"session error.*receiver": {
        "cause": "DPP Log: Session Error (Receiver) - Problem beim Datenempfang am IAC.",
        "action": "Überprüfen Sie IAC-Logs und die Netzwerkverbindung zwischen DPP und IAC."
    },
     r"dataError = ([^0].*)": {
        "cause": "GPU/IRC Log: dataError Code '{0}' gemeldet (0 ist normal).",
        "action": "Untersuchen Sie GPU/IRC-Logs auf spezifische Fehler. Prüfen Sie Datenfluss HCB->DPP->IRC."
    },

    # --- SCC app.log (Aus deiner Datei) ---
    r"L-3 Application going down now!!": {
        "cause": "SCC app.log: Die Hauptanwendung wird beendet.",
        "action": "Dies markiert einen Shutdown oder Neustart des Systems."
    },

    # --- NEU: Diagserv & HVPS Fehler (Basierend auf 'diagserv' Snippet) ---
    r"(FAIL-\d+ <cDevSystic::Connect>.*error failed)": {
        "cause": "Diagserv: SYSTIC-Verbindungsfehler (FAIL-6).",
        "action": "Prüfen Sie SYSTIC-Board, Kabel und Stromversorgung."
    },
    r"(FAIL-\d+ <SYSTIC> Device signaled fault.*= NO)": {
        "cause": "Diagserv: SYSTIC meldet einen Hardware-Fehler (z.B. HVPS Ready = NO, Healthy = NO).",
        "action": "Prüfen Sie die gemeldete Komponente (z.B. HVPS, DCB) im Diagserv-Log."
    },
    r"(WARN-\d+ <SYSTIC> Device signaled fault.*= NO)": {
        "cause": "Diagserv: SYSTIC meldet eine Hardware-Warnung (z.B. DCB7 Connected = NO).",
        "action": "Prüfen Sie die gemeldete Komponente. Dies ist oft ein unbenutzter, aber überwachter Port."
    },
    r"(FAIL-\d+ <HVPS\d+> Device parameter Arc count = \d+ outside of range)": {
        "cause": "Diagserv: HVPS meldet 'Arc count' außerhalb des zulässigen Bereichs.",
        "action": "HVPS-Fehler (Lichtbögen). Siehe 'Tube Arcing' in der Doku. HV-Verbindungen prüfen."
    },
    r"(FAIL-\d+ <HVPS\d+> Device signaled fault 'Fault flags'.*= (.*))": {
        "cause": "Diagserv: HVPS meldet Fehler-Flags: {0}.",
        "action": "Prüfen Sie die HVPS-Fehler-Flags (z.B. INT_INTLK, HV_REG). Siehe Trace.log für Details."
    },
    r"(server-src: Seasoning FAILED)": {
        "cause": "Diagserv: Das 'Tube Seasoning' (Konditionierung) ist fehlgeschlagen.",
        "action": "Überprüfen Sie die HVPS-Fehler im 'diagserv'-Log unmittelbar vor dieser Meldung."
    },
     r"server-src: \[failed\] HVPS not ready": {
        "cause": "Diagserv: HVPS meldet 'nicht bereit' während des SRC (Seasoning).",
        "action": "Überprüfen Sie die HVPS-Fehler im 'diagserv'-Log unmittelbar vor dieser Meldung."
    },
    r"(FAIL-a <::FaultHandler\(\)> System exception)": {
        "cause": "Diagserv: Kritischer Systemabsturz (System exception, 'FAIL-a').",
        "action": "Schwerwiegender Software- oder Hardwarefehler. Starten Sie das System neu. Bei Wiederholung Service kontaktieren."
    },
    r"(Connection to Diagserver is broken)": {
        "cause": "Die Verbindung zum Diagnoseserver (Diagserver) wurde unterbrochen.",
        "action": "Überprüfen Sie den Status des Diagserver-Prozesses."
    },

    # --- NEU: OptiNet Fehler (Basierend auf 'optinet' Snippet) ---
    r"(Error: ConnMgr::startTcpClient: unable to open client connection)": {
        "cause": "Optinet: Verbindung zum Server (z.B. 'mcs') konnte nicht geöffnet werden.",
        "action": "Überprüfen Sie die Netzwerkverbindung und ob der Ziel-Server (mcs) läuft."
    },
    r"(Error: bad target.*addr = ""\(null\)"")": {
        "cause": "Optinet: Interner Kommunikationsfehler (bad target, null address).",
        "action": "Software-Problem oder fehlerhafte Konfiguration. Systemneustart versuchen."
    },

    # --- KORRIGIERTER Generic/Catch-All ---
    # Dieser fängt jetzt ERROR, FATAL, FAIL, FAILED, [fault] und WARN
    r"(ERROR|FATAL|Traceback|FAILURES DETECTED|FAIL-\w+|\[failed\]|FAILED|\[fault\]|WARN-\w+)": {
        "cause": "Eine generische Fehlermeldung (ERROR, FAIL, FAILED, FAULT, WARN) wurde gefunden.",
        "action": "Überprüfen Sie die Zeile und die umliegenden Log-Einträge auf spezifischere Details zur Ursache."
    }
}


# --- KORRIGIERTE LOG_CONTEXT_RULES ---
# Hinzugefügt: FAILED, [failed], [fault], WARN
LOG_CONTEXT_RULES = [
   r"BagID",
   r"IATA",
   r"PLC",
   r"Fault cause|mfc=",
   r"NotifyHWStatus",
   r"disp_detail",
   r"tracking pec",
   r"Miss Bags S1:",
   r"TD:",
   r"SD:",
   r"XBDP",
   r"SBDP",
   r"disposition",
   r"exceptions =",
   r"L-3 Application going down",
   r"fault flags",
   r"Arc count",
   r"FAIL",
   r"FAILED", # NEU
   r"\[failed\]", # NEU
   r"\[fault\]", # NEU
   r"WARN", # NEU
   r"arrayData",
   r"filler",
   r"no barker",
   r"max Y",
   r"Beginning reconstruction",
   r"session error",
   r"dataError =",
   r"disconnected",
   r"limitSwitch",
   r"Diagserver", 
   r"HVPS",
   r"ESTOP",
   r"ILOCK",
]