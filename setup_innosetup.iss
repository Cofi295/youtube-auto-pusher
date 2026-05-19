; ═══════════════════════════════════════════════════════════
; YouTube Auto Pusher V1.0 — Inno Setup 6 Installer Script
; by OSN OCIF
; ═══════════════════════════════════════════════════════════

#define MyAppName "YouTube Auto Pusher"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "OSN OCIF"
#define MyAppURL "https://t.me/CofiNguyen"
#define MyAppExeName "YouTube Auto Pusher.exe"
#define MyAppSource "A:\ALL-TOOLS\YouTube-Auto-Pusher-ver1\release\win-unpacked"
#define MyAppIcon "A:\ALL-TOOLS\YouTube-Auto-Pusher-ver1\electron-ui\assets\app-icon.ico"

[Setup]
AppId={{CF7B8A3D-9F2E-4D1A-B5C8-7E6F3A2D1B9E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} V{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=A:\ALL-TOOLS\YouTube-Auto-Pusher-ver1\electron-ui\LICENSE.txt
OutputDir=A:\ALL-TOOLS\YouTube-Auto-Pusher-ver1\release\installer
OutputBaseFilename=YouTube Auto Pusher Setup V1.0
SetupIconFile={#MyAppIcon}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
WizardResizable=yes
WizardSizePercent=120,120
DisableProgramGroupPage=auto
PrivilegesRequiredOverridesAllowed=commandline dialog
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\app-icon.ico
UninstallDisplayName={#MyAppName} V{#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

[Files]
Source: "{#MyAppSource}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyAppIcon}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app-icon.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app-icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\cache"

[Code]
function InitializeSetup: Boolean;
begin
  Result := True;
end;
