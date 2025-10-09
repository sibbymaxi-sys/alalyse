; Script-Datei f�r Inno Setup
; Dies erstellt einen Installer f�r die GateView-Anwendung.

[Setup]
; Das ist der Name deiner Anwendung, der im Installationsprogramm und im Startmen� angezeigt wird.
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
; Standard-Name des Startmen�-Ordners.
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
; Definiert optionale Aufgaben f�r den Benutzer, wie das Erstellen von Verkn�pfungen.
; Name: Die interne Bezeichnung. Description: Der Text im Installationsdialog.
Name: desktopicon; Description: Desktop-Verkn�pfung erstellen
Name: quicklaunchicon; Description: Startmen�-Verkn�pfung erstellen

[Files]
; Die Quellpfade m�ssen relativ zum .iss-Skript sein.
; Hier f�gst du deine PyInstaller-EXE hinzu.
Source: "dist\GateView.exe"; DestDir: "{app}"; Flags: ignoreversion
; F�ge alle anderen Dateien hinzu, die PyInstaller nicht verpackt hat.
; Zum Beispiel:
; Source: "config.ini"; DestDir: "{app}"; Flags: ignoreversion
; Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Erstellt eine Verkn�pfung im Startmen�-Ordner.
Name: "{group}\GateView"; Filename: "{app}\GateView.exe"
; Erstellt eine Verkn�pfung auf dem Desktop, wenn die 'desktopicon'-Aufgabe ausgew�hlt ist.
Name: "{autodesktop}\GateView"; Filename: "{app}\GateView.exe"; Tasks: desktopicon

[Run]
; F�hrt deine Anwendung direkt nach der Installation aus.
Filename: "{app}\GateView.exe"; Description: "GateView starten"; Flags: postinstall skipifsilent