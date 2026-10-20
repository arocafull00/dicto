#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef OutputName
  #define OutputName "Dicto-" + AppVersion + "-windows-setup"
#endif

[Setup]
AppId={{8F3C2B71-5D4E-4A9B-9C61-3E7A2D8B4F10}
AppName=Dicto
AppVersion={#AppVersion}
AppPublisher=Dicto
DefaultDirName={autopf}\Dicto
DefaultGroupName=Dicto
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
AppMutex=DictoSingleInstance
CloseApplications=yes
UninstallDisplayIcon={app}\Dicto.exe
SetupIconFile=..\dicto.ico
OutputDir=..\dist
OutputBaseFilename={#OutputName}
Compression=lzma2
WizardStyle=modern

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\Dicto\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Dicto"; Filename: "{app}\Dicto.exe"
Name: "{autodesktop}\Dicto"; Filename: "{app}\Dicto.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "Dicto"; Flags: uninsdeletevalue dontcreatekey

[Run]
Filename: "{app}\Dicto.exe"; Description: "{cm:LaunchProgram,Dicto}"; Flags: nowait postinstall skipifsilent
