; Script de Instalador Inno Setup para Windows (Português do Brasil)
; VocalFlow Studio - Live Voice FX

#define MyAppName "VocalFlow Studio - Live Voice FX"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "VocalFlow Team"
#define MyAppURL "https://github.com/souusa26/vocalflow-studio"
#define MyAppExeName "VocalFlowStudio.exe"

[Setup]
AppId={{9C893245-A67E-4E76-A4E2-4328229F881A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\VocalFlowStudio
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=..\dist_installer
OutputBaseFilename=VocalFlowStudio_Instalador_v1.0.0
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "installvbcable"; Description: "Abrir página de download oficial do VB-Audio Cable gratuito (Necessário para Discord/OBS)"; GroupDescription: "Configurações Adicionais:"

[Files]
Source: "..\dist\VocalFlowStudio\*"; DestDir: "{app}"; Excludes: "portable.txt,data\*"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; Remove only the erroneous marker left by older installers; preserve user data.
Type: files; Name: "{app}\portable.txt"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
Filename: "https://vb-audio.com/Cable/"; Tasks: installvbcable; Flags: shellexec runmaximized postinstall nowait skipifsilent
