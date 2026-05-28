; ═══════════════════════════════════════════════════════════════════════
;  YouTube Auto Pusher V1.0  —  Inno Setup 6  Professional Installer
;  Publisher : OSN OCIF  |  2026
; ═══════════════════════════════════════════════════════════════════════

#define MyAppName        "YouTube Auto Pusher"
#define MyAppVersion     "1.0.0"
#define MyAppPublisher   "OSN OCIF"
#define MyAppURL         "https://t.me/CofiNguyen"
#define MyAppExeName     "YouTube Auto Pusher.exe"
#define MyAppDescription "Tu dong dang video YouTube da kenh"
#define MyAppSource      "A:\ALL-TOOLS\YouTube-Auto-Pusher-ver1\release\win-unpacked"
#define MyAppIcon        "A:\ALL-TOOLS\YouTube-Auto-Pusher-ver1\electron-ui\assets\app-icon.ico"
#define MyLicense        "A:\ALL-TOOLS\YouTube-Auto-Pusher-ver1\electron-ui\LICENSE.txt"
#define MyOutDir         "A:\ALL-TOOLS\YouTube-Auto-Pusher-ver1\release\installer"

; ───────────────────────────────────────────────────────────────────────
[Setup]
; --- Identity ---
AppId={{CF7B8A3D-9F2E-4D1A-B5C8-7E6F3A2D1B9E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} V{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright=Copyright (C) 2026 {#MyAppPublisher}

; --- Version info embedded in Setup.exe properties ---
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoCopyright=Copyright (C) 2026 {#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}.0

; --- Install location (per-user, no admin needed) ---
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; --- Privileges ---
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline

; --- Architecture: 64-bit only ---
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

; --- Minimum Windows 10 ---
MinVersion=10.0.17763

; --- Output ---
OutputDir={#MyOutDir}
OutputBaseFilename=YouTube-Auto-Pusher-Setup-V{#MyAppVersion}
SetupIconFile={#MyAppIcon}

; --- Compression ---
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; --- Wizard ---
WizardStyle=modern
ShowLanguageDialog=no

; --- License ---
LicenseFile={#MyLicense}

; --- Uninstall entry ---
UninstallDisplayIcon={app}\app-icon.ico
UninstallDisplayName={#MyAppName} V{#MyAppVersion}
UninstallRestartComputer=no

; --- Auto-close running instances (shows professional close dialog) ---
CloseApplications=yes
CloseApplicationsFilter=YouTube Auto Pusher.exe,api_server.exe
RestartApplications=no

; --- Estimated install size (~300 MB) ---
ExtraDiskSpaceRequired=314572800

; ───────────────────────────────────────────────────────────────────────
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; ───────────────────────────────────────────────────────────────────────
[Messages]
WelcomeLabel1=Chao mung ban den voi tro ly cai dat%n[#MyAppName]
WelcomeLabel2=Phan mem nay se duoc cai dat vao may tinh cua ban.%n%nVui long dong tat ca ung dung khac truoc khi tiep tuc, de tranh loi trong qua trinh cai dat.%n%nNhan Tiep theo de bat dau.
FinishedLabel=Da cai dat xong {#MyAppName}.%n%nNhan Hoan thanh de thoat khoi trinh cai dat.
SelectDirLabel3=Phan mem se duoc cai dat vao thu muc sau.
SelectDirBrowseLabel=De chon thu muc khac, nhan Duyet.
ReadyLabel1=Da san sang cai dat {#MyAppName} vao may tinh cua ban.
ReadyLabel2a=Nhan Cai dat de bat dau, hoac nhan Quay lai neu ban muon xem lai cai dat.
StatusRollback=Dang hoan tac thay doi...
StatusUninstalling=Dang go cai dat %1...
UninstallAppFullTitle=Go cai dat {#MyAppName}
ConfirmUninstall=Ban co chac muon go cai dat toan bo {#MyAppName} khong?
UninstallStatusLabel=Vui long doi trong khi {#MyAppName} dang duoc go cai dat khoi may tinh cua ban.
UninstallNotFound=File "%1" khong ton tai. Khong the go cai dat.

; ───────────────────────────────────────────────────────────────────────
[CustomMessages]
TaskDesktop=Tao &bieu tuong tren Desktop
TaskStartup=Tu dong &khoi dong cung Windows
LaunchAfterInstall=Mo {#MyAppName} ngay bay gio
UninstallKeepData=Ban co muon giu lai du lieu khong?

; ───────────────────────────────────────────────────────────────────────
[Tasks]
Name: "desktopicon"; \
  Description: "{cm:TaskDesktop}"; \
  GroupDescription: "{cm:AdditionalIcons}"; \
  Flags: checkedonce

Name: "startup"; \
  Description: "{cm:TaskStartup}"; \
  GroupDescription: "{cm:AdditionalIcons}"; \
  Flags: unchecked

; ───────────────────────────────────────────────────────────────────────
[Files]
Source: "{#MyAppSource}\*"; \
  DestDir: "{app}"; \
  Flags: ignoreversion recursesubdirs createallsubdirs

Source: "{#MyAppIcon}"; \
  DestDir: "{app}"; \
  DestName: "app-icon.ico"; \
  Flags: ignoreversion

; ───────────────────────────────────────────────────────────────────────
[Icons]
Name: "{group}\{#MyAppName}"; \
  Filename: "{app}\{#MyAppExeName}"; \
  IconFilename: "{app}\app-icon.ico"; \
  Comment: "Tu dong dang video YouTube da kenh"

Name: "{group}\Go cai dat {#MyAppName}"; \
  Filename: "{uninstallexe}"; \
  IconFilename: "{app}\app-icon.ico"

Name: "{autodesktop}\{#MyAppName}"; \
  Filename: "{app}\{#MyAppExeName}"; \
  IconFilename: "{app}\app-icon.ico"; \
  Comment: "Tu dong dang video YouTube da kenh"; \
  Tasks: desktopicon

; ───────────────────────────────────────────────────────────────────────
[Registry]
; Startup with Windows
Root: HKCU; \
  Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; \
  ValueName: "{#MyAppName}"; \
  ValueData: """{app}\{#MyAppExeName}"""; \
  Flags: uninsdeletevalue; \
  Tasks: startup

; Add/Remove Programs extra metadata
Root: HKCU; \
  Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{CF7B8A3D-9F2E-4D1A-B5C8-7E6F3A2D1B9E}_is1"; \
  ValueType: string; \
  ValueName: "HelpLink"; \
  ValueData: "{#MyAppURL}"; \
  Flags: uninsdeletevalue

Root: HKCU; \
  Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{CF7B8A3D-9F2E-4D1A-B5C8-7E6F3A2D1B9E}_is1"; \
  ValueType: string; \
  ValueName: "URLInfoAbout"; \
  ValueData: "{#MyAppURL}"; \
  Flags: uninsdeletevalue

Root: HKCU; \
  Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{CF7B8A3D-9F2E-4D1A-B5C8-7E6F3A2D1B9E}_is1"; \
  ValueType: dword; \
  ValueName: "EstimatedSize"; \
  ValueData: "307200"; \
  Flags: uninsdeletevalue

; ───────────────────────────────────────────────────────────────────────
[Run]
Filename: "{app}\{#MyAppExeName}"; \
  Description: "{cm:LaunchAfterInstall}"; \
  Flags: nowait postinstall skipifsilent shellexec

; ───────────────────────────────────────────────────────────────────────
[InstallDelete]
; Xoa DB cu khi cai de tranh loi schema conflict
Type: files; Name: "{app}\data\openclaw_bridge.db"
Type: files; Name: "{app}\data\openclaw_bridge.db-shm"
Type: files; Name: "{app}\data\openclaw_bridge.db-wal"
Type: files; Name: "{app}\openclaw_bridge.db"
Type: files; Name: "{app}\openclaw_bridge.db-shm"
Type: files; Name: "{app}\openclaw_bridge.db-wal"

; ───────────────────────────────────────────────────────────────────────
[Code]

var
  _KeepData: Boolean;

// Kiem tra he thong: 64-bit bat buoc
function InitializeSetup(): Boolean;
begin
  Result := True;
  if not IsWin64 then begin
    SuppressibleMsgBox(
      '{#MyAppName} yeu cau Windows 10 64-bit tro len.' + #13#10 +
      'May tinh cua ban dang chay Windows 32-bit.' + #13#10#13#10 +
      'Vui long nang cap he dieu hanh.',
      mbError, MB_OK, IDOK
    );
    Result := False;
  end;
end;

procedure InitializeWizard();
begin
  _KeepData := True;
end;

// Hoi giu hay xoa du lieu khi go cai dat
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDir: String;
begin
  if CurUninstallStep = usAppMutexCheck then
  begin
    if MsgBox(
      'Ban co muon giu lai du lieu cua {#MyAppName}?' + #13#10#13#10 +
      '- Chon "Co" de giu profiles, OAuth tokens va lich dang video.' + #13#10 +
      '- Chon "Khong" de xoa sach hoan toan.',
      mbConfirmation, MB_YESNO
    ) = IDYES then
      _KeepData := True
    else
      _KeepData := False;
  end;

  if CurUninstallStep = usPostUninstall then
  begin
    if not _KeepData then
    begin
      AppDir := ExpandConstant('{app}');
      if DirExists(AppDir + '\data')     then DelTree(AppDir + '\data',     True, True, True);
      if DirExists(AppDir + '\profiles') then DelTree(AppDir + '\profiles', True, True, True);
      if DirExists(AppDir + '\cache')    then DelTree(AppDir + '\cache',    True, True, True);
      if DirExists(AppDir + '\tokens')   then DelTree(AppDir + '\tokens',   True, True, True);
      if DirExists(AppDir + '\config')   then DelTree(AppDir + '\config',   True, True, True);
      DeleteFile(AppDir + '\openclaw_bridge.db');
      DeleteFile(AppDir + '\openclaw_bridge.db-shm');
      DeleteFile(AppDir + '\openclaw_bridge.db-wal');
    end;
  end;
end;

// Don sach thu muc cai dat neu trong sau khi go
procedure DeinitializeUninstall();
begin
  RemoveDir(ExpandConstant('{app}'));
end;
