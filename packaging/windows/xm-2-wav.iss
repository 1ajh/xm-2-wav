; Inno Setup script for XM-2-WAV (https://jrsoftware.org/isinfo.php)
; Build the exe first (./build.ps1), then compile this with the Inno Setup Compiler
; to produce dist\XM-2-WAV-Setup.exe. The plain dist\XM-2-WAV.exe already runs without
; installing — this installer just adds Start Menu / desktop shortcuts and an uninstaller.

#define AppName "XM-2-WAV"
#define AppVersion "1.2.0"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=ajh
AppPublisherURL=https://ajh.wtf
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\XM-2-WAV.exe
OutputDir=dist
OutputBaseFilename=XM-2-WAV-Setup
SetupIconFile=assets\xm2wav.ico
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\XM-2-WAV.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\XM-2-WAV.exe"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\XM-2-WAV.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\XM-2-WAV.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
