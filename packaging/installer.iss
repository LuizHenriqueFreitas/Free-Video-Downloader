; packaging/installer.iss - Inno Setup 6 script of the Windows installer.
;
; Packs the PyInstaller output (packaging/out/dist/GetMediaFree) into
; packaging/out/installer/GetMediaFree-<version>-Setup.exe
; Built by packaging/build.ps1, which passes the version read from
; src/services/updater.py:  ISCC.exe /DAppVersion=2.6.0 packaging\installer.iss
;
; Default install is per user, without admin (%LOCALAPPDATA%\Programs);
; the wizard lets the user choose "all users" (Program Files, asks admin).
; The language chosen on the first installer screen is also the app language:
; it's written to {app}\language.ini, read by src/core/i18n.py.
; This file is UTF-8 with BOM, needed for the accented messages below.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "Get Media Free"
#define AppExe "GetMediaFree.exe"
#define DistDir "out\dist\GetMediaFree"

[Setup]
; never change AppId: it's how upgrades and the uninstaller find the installation
AppId={{AF85F74E-39F0-4921-B958-35F645DE597B}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Get Media Free
AppPublisherURL=https://github.com/LuizHenriqueFreitas/Get-Media-Free
AppSupportURL=https://github.com/LuizHenriqueFreitas/Get-Media-Free/issues
AppUpdatesURL=https://github.com/LuizHenriqueFreitas/Get-Media-Free/releases
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
LicenseFile=..\LICENSE
SetupIconFile=..\src\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
OutputDir=out\installer
OutputBaseFilename=GetMediaFree-{#AppVersion}-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; always ask the language (preselected from the Windows language) - it's the app language too
ShowLanguageDialog=yes
LanguageDetectionMethod=uilanguage
; closes a running Get Media Free before replacing its files
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
brazilianportuguese.RemoveUserData=Deseja apagar também seus dados do Get Media Free (histórico, configurações e cookies importados)?
english.RemoveUserData=Do you also want to delete your Get Media Free data (history, settings and imported cookies)?

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; upgrade: drop files of the previous version that the new one doesn't ship
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[INI]
; app language = installer language ("brazilianportuguese" / "english", see [Languages])
Filename: "{app}\language.ini"; Section: "Settings"; Key: "Language"; String: "{language}"

[UninstallDelete]
Type: files; Name: "{app}\language.ini"

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// user data lives outside {app} (see get_app_data_dir() at src/core/utils.py),
// so it's only removed when the user agrees - it holds history and cookies
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{localappdata}\GetMediaFree');
    if DirExists(DataDir) and not UninstallSilent then
      if MsgBox(CustomMessage('RemoveUserData'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(DataDir, True, True, True);
  end;
end;
