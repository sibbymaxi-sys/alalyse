# help_texts.py

GATEVIEW_HELP_TEXT = """
Willkommen beim GateView Analyzer!

Dieses Werkzeug dient zur Analyse und Zusammenführung von Log-Dateien aus ClearScan-Handgepäckanlagen. Es ermöglicht eine chronologische Darstellung des Weges einer Wanne durch das System, von der Erfassung im Scanner bis zur Sortierung durch die SPS.

---------------------------------
Grundlegender Arbeitsablauf
---------------------------------

1.  **Logs laden:** Öffnen Sie nacheinander die verschiedenen Log-Dateien (Scanner, OMS, PLC). Beachten Sie dabei die empfohlene Ladereihenfolge.
2.  **Übersicht ansehen:** Die Haupttabelle zeigt eine Zusammenfassung aller erkannten Wannen-Durchläufe ("Reisen").
3.  **Filtern und Suchen:** Verwenden Sie die Filter, um schnell eine bestimmte BagID oder IATA (Wannen-Nummer) zu finden.
4.  **Detail-Analyse:** Doppelklicken Sie auf einen Eintrag, um ein detailliertes Fenster mit der chronologischen Klartext-Analyse und den originalen Log-Auszügen für diesen spezifischen Durchlauf zu öffnen.
5.  **Exportieren:** Im Detail-Fenster können Sie die vollständige Analyse als Text-Datei oder PDF speichern.

---------------------------------
Wichtiger Hinweis zur Ladereihenfolge
---------------------------------

Damit die Analyse korrekt funktioniert, laden Sie die Log-Dateien bitte immer in der folgenden Reihenfolge:

1.  **IMMER ZUERST: Scanner-Log (`scanner_bag.log`)**
    * Verwenden Sie den Button: **"1. Scanner-Log öffnen"**.
    * **Grund:** Der Scanner-Log ist der Anker für jede Reise. Das Laden einer neuen Scanner-Datei setzt die gesamte Analyse zurück und startet eine saubere, neue Auswertung.

2.  **DANACH: OMS-Log (`oms.log`) hinzufügen**
    * Verwenden Sie den Button: **"2. OMS-Log hinzufügen"**.
    * **Grund:** Dieser Schritt reichert die bereits erkannten Scanner-Reisen mit den Status-Informationen des Operations Management Systems an.

3.  **ZULETZT: PLC-Log (`PlcLog.csv` oder `.log`) hinzufügen**
    * Verwenden Sie den Button: **"BRAVA TRS Logs laden"**.
    * **Grund:** Dieser letzte Schritt fügt die finalen, physischen Sortier-Informationen von der Anlagensteuerung (SPS/PLC) hinzu und vervollständigt den Weg der Wanne.

---------------------------------
Funktionen im Detail
---------------------------------

* **Scanner-Log öffnen:** Startet eine neue Analyse. Alle bisherigen Daten werden gelöscht.
* **OMS-Log hinzufügen:** Fügt OMS-Daten zur bestehenden Analyse hinzu.
* **BRAVA TRS Logs laden:** Fügt SPS/PLC-Daten (aus PlcLog.csv) zur bestehenden Analyse hinzu.
* **System-Analyse:** Ein separates Werkzeug zur Analyse von allgemeinen System-Logs auf Fehler und Warnungen.
* **Analyse zurücksetzen:** Leert alle geladenen Daten und setzt die Anwendung in den Startzustand zurück.

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

**1. Logs Laden**

* **Log-Ordner auswählen:** Klicken Sie auf diesen Button, um den Hauptordner auszuwählen, der die MV3D Logs enthält (z.B. einen entpackten Log-Dump). Die App durchsucht diesen Ordner und alle Unterordner nach bekannten Log-Dateien (scs.log, bms.log, plc.log, dcs.log, dpp.log, trace.log, etc.) sowie der neuesten diagserv.* Datei.
* **Zeitraum:** Standardmäßig werden nur Log-Einträge der **letzten Woche** (basierend auf dem neuesten gefundenen Zeitstempel) geladen, um die Ladezeit zu verkürzen.
* **Ganzen Zeitraum laden:** Wenn Sie alle verfügbaren Log-Einträge aus dem ausgewählten Ordner laden möchten (ohne Zeitlimit), klicken Sie *nach* der Auswahl des Ordners auf diesen Button. Dies kann bei großen Datenmengen länger dauern.

**2. Fehlerübersicht (Hauptfenster)**

* **Liste:** Zeigt alle gefundenen Fehler, Warnungen und relevanten Systemmeldungen aus den geladenen Logs an.
* **Spalten:**
    * *Zeitpunkt:* Zeitstempel des Log-Eintrags.
    * *Quelldatei:* Name der Log-Datei, aus der der Eintrag stammt.
    * *Fehlermeldung:* Der originale Log-Eintrag.
* **Hervorhebungen:**
    * **Fett:** Zeilen, die einem bekannten Fehler aus der `mv3d_error_definitions`-Datei entsprechen.
    * <span style="background-color:#4B2525; color:white;">Roter Hintergrund</span>: Allgemeine Fehler und Warnungen.
    * <span style="color:#6495ED;">Blaue Schrift</span>: Systemstarts, Neustarts oder Wiederherstellungen von Verbindungen.

**3. Filter & Suche**

Verwenden Sie die Filterleisten oberhalb der Liste, um die angezeigten Fehler einzugrenzen:

* **Schnellfilter (Buttons):** Klicken Sie auf Buttons wie "E-Stop (16)", "HVPS (30)", "RTR Down (38-40)" etc., um schnell nur Fehler mit dem entsprechenden Fehlercode (FC) anzuzeigen. Der Button "HVPS (Alle)" filtert nach allen bekannten HVPS-bezogenen Meldungen.
* **Zeitraum:** Wählen Sie ein Start- und Enddatum aus, um nur Fehler innerhalb dieses Zeitraums anzuzeigen. Klicken Sie auf das Kalendersymbol oder geben Sie das Datum im Format YYYY-MM-DD ein.
* **Datei:** Wählen Sie eine spezifische Log-Datei aus dem Dropdown-Menü aus, um nur Fehler aus dieser Datei anzuzeigen. Wählen Sie "Alle", um keine Dateifilterung anzuwenden.
* **Fehlercode (FC):** Geben Sie eine Zahl ein (z.B. `17` für Interlock), um nur Zeilen anzuzeigen, die `mfc=17`, `fault_cause = 17` oder `(FC 17)` enthalten. Drücken Sie Enter oder klicken Sie auf "Suchen/Filtern Anwenden".
* **Suchen:** Geben Sie einen beliebigen Text ein (z.B. `Arc count`, `BagID`, eine IP-Adresse), um alle Zeilen zu finden, die diesen Text enthalten (Groß-/Kleinschreibung wird ignoriert). Drücken Sie Enter oder klicken Sie auf "Suchen/Filtern Anwenden".
* **Regex:** Aktivieren Sie diese Checkbox, wenn Ihre Eingabe im "Suchen"-Feld als regulärer Ausdruck (Regex) interpretiert werden soll (für fortgeschrittene Suchen).
* **Suchen/Filtern Anwenden:** Wendet alle aktuell eingestellten Filter (Datum, Datei, FC, Suche) auf die Liste an.
* **Alle Filter zurücksetzen:** Setzt alle Filter (Datum, Datei, FC, Suche) auf die Standardwerte zurück und zeigt wieder alle gefundenen Fehler im geladenen Zeitraum an.

**4. Detail-Analyse (Doppelklick)**

* **Doppelklicken** Sie auf eine Zeile in der Fehlerliste, um das Detailfenster zu öffnen.
* **Fehler-Analyse:** Zeigt die erkannte Ursache und Handlungsempfehlung aus der `mv3d_error_definitions`, falls der Fehler bekannt ist.
* **Log-Kontext:** Zeigt die 20 Log-Zeilen *vor* und *nach* dem ausgewählten Fehler an, **chronologisch sortiert aus allen geladenen Dateien**. Dies hilft, Zusammenhänge zu erkennen.
* **Hervorhebungen im Kontext:** Wichtige Schlüsselwörter (wie `BagID`, `PLC`, `mfc=`, `fault flags`, `disconnected` etc.) sind im Kontext <span style="background-color:#6A4D00; color:white;">farbig markiert</span>.
* **Scrollen:** Sie können den Log-Kontext horizontal und vertikal scrollen.
* **Kopieren:** Klicken Sie auf "Log-Kontext kopieren", um den gesamten angezeigten Kontext in die Zwischenablage zu kopieren.

**5. Empfohlene Vorgehensweise zur Fehlersuche**

1.  Laden Sie den Log-Ordner (Standardmäßig letzte Woche).
2.  Suchen Sie im Hauptfenster nach dem ersten relevanten Fehler (oft `mfc=` oder `fault_cause =` ungleich 0 in `scs.log` oder `bms.log`). Nutzen Sie ggf. die Filter.
3.  Doppelklicken Sie auf den Fehler, um den Kontext zu sehen. Achten Sie auf hervorgehobene Keywords und Meldungen kurz vor dem eigentlichen Fehler.
4.  Basierend auf dem Fehlercode oder den Meldungen im Kontext, filtern Sie gezielt weiter (z.B. nach Fehlercode, nach einer bestimmten Datei wie `trace.log`, oder suchen Sie nach spezifischen Begriffen).
5.  Nutzen Sie die Informationen aus dem Detailfenster (Ursache/Aktion) als Anhaltspunkt.
6.  Wenn der Fehlerzeitraum bekannt ist, grenzen Sie den Datumsfilter ein.
7.  Wenn die letzte Woche nicht ausreicht, laden Sie über den Button "Ganzen Zeitraum laden" mehr Daten (dies kann dauern!).

Viel Erfolg bei der Analyse!




"""

# help_texts.py

GATEVIEW_HELP_TEXT = """
Willkommen beim GateView Analyzer!

Dieses Werkzeug dient zur Analyse und Zusammenführung von Log-Dateien aus ClearScan-Handgepäckanlagen. Es ermöglicht eine chronologische Darstellung des Weges einer Wanne durch das System, von der Erfassung im Scanner bis zur Sortierung durch die SPS.

---------------------------------
Wichtiger Hinweis zur Ladereihenfolge
---------------------------------

Damit die Analyse korrekt funktioniert, laden Sie die Log-Dateien bitte immer in der folgenden Reihenfolge:

1.  **IMMER ZUERST: Scanner-Log (`scanner_bag.log`)**
    * Verwenden Sie den Button: **"1. Scanner-Log öffnen"**.
    * **Grund:** Der Scanner-Log ist der Anker für jede Reise. Das Laden einer neuen Scanner-Datei setzt die gesamte Analyse zurück.

2.  **DANACH: OMS-Log (`oms.log`) hinzufügen**
    * Verwenden Sie den Button: **"2. OMS-Log hinzufügen"**.
    * **Grund:** Reichert die Analyse mit den Status-Informationen des Operations Management Systems an.

3.  **ZULETZT: PLC-Log (`PlcLog.csv` oder `.log`) hinzufügen**
    * Verwenden Sie den Button: **"BRAVA TRS Logs laden"**.
    * **Grund:** Fügt die finalen, physischen Sortier-Informationen von der Anlagensteuerung (SPS/PLC) hinzu.
"""




# ÜBERARBEITETER, RECHTSSICHERERER DISCLAIMER
DISCLAIMER_TEXT = """
Haftungsausschluss (Disclaimer)

**1. Bereitstellung "Wie Besehen" ("As-Is")**
Diese Software wird "wie besehen" und "wie verfügbar" ohne jegliche Gewährleistungen, Garantien oder Zusicherungen jeglicher Art, weder ausdrücklich noch stillschweigend, zur Verfügung gestellt. Dies schließt, ohne darauf beschränkt zu sein, stillschweigende Garantien der Marktgängigkeit, der Eignung für einen bestimmten Zweck oder der Nichtverletzung von Rechten Dritter ein. Der Entwickler garantiert nicht, dass die Software ununterbrochen, fehlerfrei, sicher oder frei von Viren oder anderen schädlichen Komponenten ist.

**2. Haftungsbeschränkung**
In keinem Fall haftet der Entwickler für direkte, indirekte, zufällige, spezielle, exemplarische oder Folgeschäden (einschließlich, aber nicht beschränkt auf Datenverlust, Betriebsunterbrechung, entgangenen Gewinn oder Rufschädigung), die aus der Nutzung, dem Missbrauch oder der Unfähigkeit zur Nutzung dieser Software entstehen, selbst wenn der Entwickler auf die Möglichkeit solcher Schäden hingewiesen wurde. Die gesamte Haftung des Entwicklers übersteigt in keinem Fall den Betrag, den Sie gegebenenfalls für die Software bezahlt haben.

**3. Zweck und Verantwortung des Nutzers**
Die Software dient ausschließlich als Hilfsmittel zur Analyse und Visualisierung von Log-Dateien. Die dargestellten Ergebnisse sind eine computergestützte Interpretation der zugrundeliegenden Daten und erheben keinen Anspruch auf Vollständigkeit, Fehlerfreiheit oder absolute Genauigkeit.

Der Nutzer trägt die alleinige Verantwortung für die Überprüfung und Validierung der Ergebnisse. Jegliche Entscheidungen, Handlungen oder Unterlassungen, die auf Grundlage der von dieser Software dargestellten Informationen getroffen werden, geschehen auf eigenes Risiko des Nutzers. Der Entwickler übernimmt keine Verantwortung für die Konsequenzen solcher Entscheidungen.

**4. Keine Garantie für Datenintegrität**
Der Entwickler ist nicht für die Genauigkeit, Zuverlässigkeit, Integrität oder Aktualität der Log-Dateien verantwortlich, die mit dieser Software analysiert werden. Fehler in den Quelldaten können zu fehlerhaften Analyseergebnissen führen.

Durch die Nutzung dieser Software erkennen Sie an, dass Sie diesen Haftungsausschluss gelesen, verstanden und akzeptiert haben.
"""