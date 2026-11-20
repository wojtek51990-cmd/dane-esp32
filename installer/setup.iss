#define MyAppName "ESP32 Data Monitor"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ESP32 Data Monitor"
#define MyAppExeName "ESP32-Data-Monitor.exe"

[Setup]
AppId={{C0F3D2A1-89F4-4B8A-9CC0-1234567890AB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\ESP32 Data Monitor
DefaultGroupName={#MyAppName}
OutputDir=Output
OutputBaseFilename=ESP32-Data-Monitor-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "desktopicon"; Description: "Utwórz skrót na pulpicie"; GroupDescription: "Dodatkowe skróty:"; Flags: unchecked

[Files]
Source: "..\dist\ESP32-Data-Monitor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ESP32 Data Monitor"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\ESP32 Data Monitor"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Uruchom ESP32 Data Monitor"; Flags: postinstall nowait skipifsilent
