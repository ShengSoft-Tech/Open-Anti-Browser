; Inno Setup script for Open-Anti-Browser (fork build by ShengSoft-Tech)
; Packages the PyInstaller --onedir output (app + bundled engines) into an
; offline Windows installer: Open-Anti-Browser-Setup.exe
;
; Invoked from CI as:
;   ISCC.exe /DMyAppVersion=0.1.8 /DRepoRoot=<repo root> .github\installer.iss

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#ifndef RepoRoot
  #define RepoRoot "."
#endif
#define MyAppName "Open-Anti-Browser"
#define MyAppExe "Open-Anti-Browser.exe"

[Setup]
AppId={{B5E6A9C1-9A3E-4E2B-9C1A-0A7F4B2D8E10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=ShengSoft-Tech
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#RepoRoot}\installer_out
OutputBaseFilename=Open-Anti-Browser-Setup
SetupIconFile={#RepoRoot}\assets\app.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#RepoRoot}\dist\Open-Anti-Browser\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
