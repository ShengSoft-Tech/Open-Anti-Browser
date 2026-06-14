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

[UninstallDelete]
Type: files; Name: "{app}\bind-host.txt"

[Code]
var
  HostPage: TInputQueryWizardPage;

{ Read /HOST=<addr> from the installer command line (for silent installs). }
function GetHostParam(): String;
var
  i: Integer;
  s: String;
begin
  Result := '';
  for i := 1 to ParamCount do
  begin
    s := ParamStr(i);
    if CompareText(Copy(s, 1, 6), '/HOST=') = 0 then
      Result := Copy(s, 7, Length(s));
  end;
end;

procedure InitializeWizard();
var
  def: String;
begin
  HostPage := CreateInputQueryPage(wpSelectDir,
    'Server bind address',
    'Which address should the local server listen on?',
    'Enter 127.0.0.1 for local-only access, or 0.0.0.0 to allow access from other machines on the network. Saved to bind-host.txt in the install folder.');
  HostPage.Add('Bind host:', False);
  def := Trim(GetHostParam());
  if def = '' then
    def := '127.0.0.1';
  HostPage.Values[0] := def;
end;

function ResolvedHost(): String;
begin
  Result := Trim(HostPage.Values[0]);
  if Result = '' then
    Result := '127.0.0.1';
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    SaveStringToFile(ExpandConstant('{app}\bind-host.txt'), ResolvedHost(), False);
end;
