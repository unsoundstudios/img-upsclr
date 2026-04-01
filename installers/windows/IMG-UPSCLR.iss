; Inno Setup script for IMG-UPSCLR

#define MyAppName "IMG-UPSCLR"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Unsound Studios"
#define MyAppExeName "IMG-UPSCLR.exe"

[Setup]
AppId={{2D95B8D8-8DF5-44CE-8A2F-758D23F3E8C4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\IMG-UPSCLR
DefaultGroupName=IMG-UPSCLR
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=IMG-UPSCLR-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"

[Files]
Source: "..\..\dist\IMG-UPSCLR\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\SECURITY.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\IMG-UPSCLR"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\IMG-UPSCLR"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch IMG-UPSCLR"; Flags: nowait postinstall skipifsilent
