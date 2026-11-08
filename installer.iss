#define MyAppName "Trợ lý dự toán ngân sách xã"
#define MyAppVersion "0.8.6-beta"
#define MyAppExeName "TroLyDuToanXa.exe"
[Setup]
AppId={{A6A8DCE5-76B5-44B9-BF08-C7A9F6F1E3E4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\TroLyDuToanXa
DefaultGroupName={#MyAppName}
OutputDir=output
OutputBaseFilename=Setup_TroLyDuToanXa_Win10_Win11
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
[Files]
Source: "dist\TroLyDuToanXa.exe"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Tạo biểu tượng ngoài màn hình"; GroupDescription: "Tùy chọn:"
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Mở phần mềm"; Flags: nowait postinstall skipifsilent
