; Script-Datei für Inno Setup
; Dies erstellt einen Installer für die GateView-Anwendung.

[Setup]
; Das ist der Name deiner Anwendung, der im Installationsprogramm und im Startmenü angezeigt wird.
AppName=GateView
AppVersion=1.0
; AppPublisher ist der Name deines Unternehmens oder deines Projekts.
AppPublisher=Dein Name / Dein Projekt
; Die URL der App-Homepage (optional).
AppPublisherURL=
AppSupportURL=
AppUpdatesURL=
; Das ist der Name der finalen Installationsdatei.
OutputBaseFilename=GateView Installer
; Das Verzeichnis, in dem die Installationsdatei erstellt wird.
OutputDir=.\dist
; Standard-Installationsverzeichnis (z.B. C:\Program Files\GateView)
DefaultDirName={autopf}\GateView
; Standard-Name des Startmenü-Ordners.
DefaultGroupName=GateView
; Zeigt das 'Fertigstellen'-Fenster am Ende der Installation.
CloseApplications=yes
CloseApplicationsFilter=GateView.exe
DisableProgramGroupPage=yes
; Erstellt einen Uninstaller.
UninstallDisplayIcon={app}\GateView.exe
UninstallDisplayName=GateView deinstallieren
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin

[Tasks]
; Definiert optionale Aufgaben für den Benutzer, wie das Erstellen von Verknüpfungen.
; Name: Die interne Bezeichnung. Description: Der Text im Installationsdialog.
Name: desktopicon; Description: Desktop-Verknüpfung erstellen
Name: quicklaunchicon; Description: Startmenü-Verknüpfung erstellen

[Files]
; Die Quellpfade müssen relativ zum .iss-Skript sein.
; Hier fügst du deine PyInstaller-EXE hinzu.
Source: "dist\GateView.exe"; DestDir: "{app}"; Flags: ignoreversion
; Füge alle anderen Dateien hinzu, die PyInstaller nicht verpackt hat.
; Zum Beispiel:
; Source: "config.ini"; DestDir: "{app}"; Flags: ignoreversion
; Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Erstellt eine Verknüpfung im Startmenü-Ordner.
Name: "{group}\GateView"; Filename: "{app}\GateView.exe"
; Erstellt eine Verknüpfung auf dem Desktop, wenn die 'desktopicon'-Aufgabe ausgewählt ist.
Name: "{autodesktop}\GateView"; Filename: "{app}\GateView.exe"; Tasks: desktopicon

[Run]
; Führt deine Anwendung direkt nach der Installation aus.
Filename: "{app}\GateView.exe"; Description: "GateView starten"; Flags: postinstall skipifsilent