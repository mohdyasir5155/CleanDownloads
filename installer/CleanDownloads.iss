; CleanDownloads Inno Setup Script
; Production Windows Installer for CleanDownloads CLI
; Standard Per-User Installation (No Administrator Privileges Required)

#define MyAppName "CleanDownloads"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "CleanDownloads"
#define MyAppURL "https://github.com/cleandownloads/CleanDownloads"
#define MyAppExeName "cleandownloads.exe"

[Setup]
AppId={{9B560C62-E764-4FD3-909E-D6A7862E8F48}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\Programs\CleanDownloads
DisableDirPage=auto
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=CleanDownloads-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesEnvironment=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
CloseApplications=force

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; DestName: "README.md"; Flags: ignoreversion

[Code]
// Broadcast environment changes so new cmd/PowerShell windows see updated PATH
const
  WM_SETTINGCHANGE = $001A;
  SMTO_ABORTIFHUNG = $0002;

function SendMessageTimeout(
  hWnd: HWND;
  Msg: Cardinal;
  wParam: LongInt;
  lParam: String;
  fuFlags: Cardinal;
  uTimeout: Cardinal;
  out lpdwResult: Cardinal
): LongInt; external 'SendMessageTimeoutW@user32.dll stdcall';

procedure BroadcastEnvironmentChange();
var
  DummyResult: Cardinal;
begin
  SendMessageTimeout(
    HWND_BROADCAST,
    WM_SETTINGCHANGE,
    0,
    'Environment',
    SMTO_ABORTIFHUNG,
    5000,
    DummyResult
  );
end;

function NormalizePath(P: String): String;
begin
  Result := Trim(P);
  while (Length(Result) > 0) and (Result[Length(Result)] = '\') do
    Delete(Result, Length(Result), 1);
end;

procedure AddAppDirToUserPath();
var
  CurrentPath: String;
  AppDir: String;
  NormAppDir: String;
  I: Integer;
  AlreadyPresent: Boolean;
begin
  AppDir := ExpandConstant('{app}');
  NormAppDir := NormalizePath(AppDir);
  AlreadyPresent := False;

  if RegQueryStringValue(HKCU, 'Environment', 'Path', CurrentPath) then
  begin
    // Split on semicolon
    CurrentPath := Trim(CurrentPath);
    if Length(CurrentPath) > 0 then
    begin
      // Search for existing entry
      I := Pos(';' + Lowercase(NormAppDir) + ';', ';' + Lowercase(CurrentPath) + ';');
      if I > 0 then
        AlreadyPresent := True;
    end;
  end
  else
    CurrentPath := '';

  if not AlreadyPresent then
  begin
    if Length(CurrentPath) > 0 then
    begin
      if CurrentPath[Length(CurrentPath)] = ';' then
        CurrentPath := CurrentPath + AppDir
      else
        CurrentPath := CurrentPath + ';' + AppDir;
    end
    else
      CurrentPath := AppDir;

    if RegWriteStringValue(HKCU, 'Environment', 'Path', CurrentPath) then
      BroadcastEnvironmentChange();
  end;
end;

procedure RemoveAppDirFromUserPath();
var
  CurrentPath: String;
  AppDir: String;
  NormAppDir: String;
  NewPath: String;
  I: Integer;
  EntryNorm: String;
  HasChanges: Boolean;
begin
  AppDir := ExpandConstant('{app}');
  NormAppDir := NormalizePath(AppDir);
  HasChanges := False;

  if RegQueryStringValue(HKCU, 'Environment', 'Path', CurrentPath) then
  begin
    // Custom semicolon split
    NewPath := '';
    while Pos(';', CurrentPath) > 0 do
    begin
      I := Pos(';', CurrentPath);
      EntryNorm := NormalizePath(Copy(CurrentPath, 1, I - 1));
      Delete(CurrentPath, 1, I);

      if Length(EntryNorm) > 0 then
      begin
        if Lowercase(EntryNorm) = Lowercase(NormAppDir) then
          HasChanges := True
        else
        begin
          if Length(NewPath) > 0 then
            NewPath := NewPath + ';' + EntryNorm
          else
            NewPath := EntryNorm;
        end;
      end;
    end;

    // Remaining last element
    EntryNorm := NormalizePath(CurrentPath);
    if Length(EntryNorm) > 0 then
    begin
      if Lowercase(EntryNorm) = Lowercase(NormAppDir) then
        HasChanges := True
      else
      begin
        if Length(NewPath) > 0 then
          NewPath := NewPath + ';' + EntryNorm
        else
          NewPath := EntryNorm;
      end;
    end;

    if HasChanges then
    begin
      if RegWriteStringValue(HKCU, 'Environment', 'Path', NewPath) then
        BroadcastEnvironmentChange();
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    AddAppDirToUserPath();
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    RemoveAppDirFromUserPath();
  end;
end;
