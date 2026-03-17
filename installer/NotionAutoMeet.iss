; ============================================================
; Notion Auto-Meet — Inno Setup Installer Script
;
; Creates a professional Windows installer with:
;   - Install to Program Files (or user-chosen directory)
;   - Start Menu & optional Desktop shortcuts
;   - Optional "Start on login" via registry
;   - System tray-style background app (no console window)
;   - Clean uninstaller (stops process, removes registry, logs)
;
; Requires: Inno Setup 6 (https://jrsoftware.org/isinfo.php)
; Build:    Run build_windows.bat or:
;           "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" NotionAutoMeet.iss
; ============================================================

#define MyAppName "Notion Auto-Meet"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Notion Auto-Meet"
#define MyAppURL "https://github.com/notion-auto-meet"
#define MyAppExeName "NotionAutoMeet.exe"
#define MyAppDescription "Automatically starts Notion AI meeting notes when a call begins"

[Setup]
AppId={{B8E4F2A1-3C5D-4E6F-A7B8-9C0D1E2F3A4B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=NotionAutoMeetSetup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Show app description on the welcome page
AppComments={#MyAppDescription}
; Minimum Windows 10
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked
Name: "autostart"; Description: "Start automatically when I sign in to Windows"; GroupDescription: "Startup:"; Flags: checkedonce

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion; DestName: "README.txt"

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "{#MyAppDescription}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
; Desktop (optional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "{#MyAppDescription}"

[Registry]
; Autostart on login (current user, removed on uninstall)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "NotionAutoMeet"; \
    ValueData: """{app}\{#MyAppExeName}"""; \
    Flags: uninsdeletevalue; Tasks: autostart

[Run]
; Offer to launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; \
    Flags: nowait postinstall skipifsilent

[UninstallRun]
; Kill running instance before uninstall
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#MyAppExeName}"; \
    Flags: runhidden skipifdoesntexist; RunOnceId: "KillApp"

[UninstallDelete]
; Clean up log file
Type: files; Name: "{app}\notion-auto-meet.log"
; Clean up app directory if empty
Type: dirifempty; Name: "{app}"

[Messages]
WelcomeLabel2=This will install [name/ver] on your computer.%n%n{#MyAppDescription}. It runs silently in the background and detects when Notion shows a meeting popup (from Zoom, Teams, Meet, etc.), then automatically clicks "Start Transcribing" so your meeting notes begin recording without any manual action.%n%nClick Next to continue.

[Code]
// Stop any running instance before installing (upgrade scenario)
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'),
       ExpandConstant('/F /IM {#MyAppExeName}'),
       '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := '';
end;
