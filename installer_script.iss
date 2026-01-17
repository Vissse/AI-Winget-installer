; -- installer_script.iss --

#define MyAppName "Univerzální aplikace"
#define MyAppVersion "7.3.9.7" ; TOTO MUSÍTE MĚNIT PŘI KAŽDÉM RELEASE
#define MyAppPublisher "Vissse"
#define MyAppExeName "AI_Winget_Installer.exe" ; Název vašeho zkompilovaného EXE z PyInstalleru

[Setup]
AppId={{C626C87C-E562-4EC8-8924-42878783456F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
; Důležité: Instalátor nebude vyžadovat admin práva, pokud instaluje jen pro uživatele
PrivilegesRequired=lowest 
OutputBaseFilename=UniversalApp_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "czech"; MessagesFile: "compiler:Languages\Czech.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Zde zadejte cestu k vašemu EXE vytvořenému PyInstallerem (v dist složce)
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent shellexec

[Registry]
; Nastaví příznak "Spustit jako správce" pro aktuálního uživatele
Root: HKCU; Subkey: "Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"; ValueType: string; ValueName: "{app}\{#MyAppExeName}"; ValueData: "~ RUNASADMIN"; Flags: uninsdeletevalue