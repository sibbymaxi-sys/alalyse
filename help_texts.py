# help_texts.py

GATEVIEW_HELP_TEXT = """
Programmbeschreibung:
Der GateView Analyzer ist ein spezialisiertes Werkzeug zur Analyse des Lebenszyklus einzelner Gepäckstücke. Es fokussiert sich auf die chronologische Abfolge von Ereignissen für eine spezifische BagID, von der Erfassung bis zur finalen Entscheidung.

----------------------------------------------------------------------
Funktionen:
----------------------------------------------------------------------

1.  Logs laden:
    - Öffnen Sie lokale Log-Dateien (`scanner_bag.log`, `OMS.log`) über die Buttons.
    - Nutzen Sie den Menüpunkt "Datei" -> "FTP-Download...", um die neuesten Logs direkt und sicher (via SFTP) von der Anlage zu laden. Profile für verschiedene Anlagen können gespeichert werden.

2.  Hauptansicht:
    - Zeigt eine Liste aller identifizierten Gepäck-Durchläufe ("Journeys").
    - Spalten: Zeitstempel des Starts, BagID, zugeordnete Wannen-ID (IATA), finaler Status und der entscheidende Operator.

3.  Detail-Analyse (Doppelklick):
    - Ein Doppelklick auf einen Eintrag öffnet die Detailansicht ("Bag History").
    - Hier sehen Sie eine Zusammenfassung der Routing-Entscheidungen und die chronologischen Log-Auszüge aus allen relevanten Quellen, die nur dieses eine Gepäckstück betreffen.

4.  Erweiterte Suche:
    - Ermöglicht die Filterung der Hauptliste nach BagID- oder IATA-Fragmenten.
    - Die Suche nach Datum ignoriert das Jahr. Sie können z.B. alle Vorfälle vom 15. November bis 10. Februar über mehrere Jahre hinweg suchen.

5.  Analyse speichern:
    - In der Detailansicht können Sie die komplette Analyse als `.txt`-Datei oder als `.pdf` (im Querformat für bessere Lesbarkeit) speichern.

----------------------------------------------------------------------
Optimaler Arbeitsablauf:
----------------------------------------------------------------------

1.  Problem-Zeitraum bekannt? Nutzen Sie "Erweiterte Suche", um die Liste einzugrenzen.
2.  Unbekannt? Laden Sie die Logs und verschaffen Sie sich einen Überblick in der Hauptliste. Sortieren Sie nach "End-Status", um Problemfälle zu finden.
3.  Doppelklicken Sie auf einen interessanten Fall, um die komplette Geschichte dieses Gepäckstücks zu sehen und die Ursache für eine Fehlleitung oder einen No-Read zu finden.
4.  Speichern Sie die Analyse als PDF, um sie zu dokumentieren oder weiterzuleiten.
"""

MV3D_HELP_TEXT = """
Programmbeschreibung:
Der MV3D System Analyzer ist ein Werkzeug zur Diagnose von komplexen Systemfehlern. Anstatt sich auf einzelne Fehler zu konzentrieren, analysiert er das Zusammenspiel aller System-Komponenten (SCS, BMS, FSM, PLC etc.), um die Ursache von Störungen wie "Overruns" oder Anlagen-Stillständen zu finden.

----------------------------------------------------------------------
Funktionen:
----------------------------------------------------------------------

1.  Logs laden:
    - Öffnen Sie ein Hauptverzeichnis. Das Programm durchsucht intelligent alle Unterordner (scs, dpp, etc.) nach den korrekten Log-Dateien.
    - Nutzen Sie "Datei" -> "FTP-Download...", um die neuesten Logs von allen relevanten Rechnern (SCC, IAC, DPP) gleichzeitig via SFTP sicher herunterzuladen. Profile mit IPs und Pfaden können gespeichert werden.

2.  Vorschau & Zeitraum-Auswahl:
    - Vor dem Laden wird eine schnelle Vorschau erstellt, die Ihnen den verfügbaren Datenzeitraum und die Gesamtanzahl der Einträge anzeigt.
    - Im folgenden Dialog können Sie den Analyse-Zeitraum eingrenzen, um die Ladezeit bei großen Datenmengen drastisch zu reduzieren. Ein Dropdown-Menü hilft bei der Schnellauswahl eines Tages.

3.  Hauptansicht ("Fall-Akten"):
    - Das Programm zeigt nicht alle Logs, sondern eine aufbereitete Liste von "Fall-Akten". Jede Fall-Akte repräsentiert ein kritisches Ereignis (z.B. einen Systemfehler oder einen Overrun).
    - Sie sehen sofort den Zeitpunkt, den Vorfalls-Typ und die wahrscheinliche Ursache.
    - Ein Dropdown-Menü erlaubt die Filterung der Fall-Akten nach Datum.

4.  Fall-Akten-Analyse (Doppelklick):
    - Ein Doppelklick auf eine Fall-Akte öffnet das Analyse-Fenster.
    - Es zeigt Ihnen eine Zusammenfassung, den System-Status *vor* dem Fehler und die chronologische "Konversation" aller beteiligten Systeme im Fehlerzeitraum.

----------------------------------------------------------------------
Optimaler Arbeitsablauf:
----------------------------------------------------------------------

1.  Laden Sie die Logs für den gewünschten Tag oder Zeitraum über "Logs laden" oder "FTP-Download".
2.  Grenzen Sie im Dialog den Zeitraum präzise ein, um die Analyse zu beschleunigen.
3.  Überprüfen Sie die Liste der erstellten Fall-Akten. Filtern Sie bei Bedarf nach einem bestimmten Tag.
4.  Doppelklicken Sie auf die relevanteste Fall-Akte, um die Fehlerkette und die Konversation der Systeme zu analysieren und so die wahre Ursache zu finden.





"""