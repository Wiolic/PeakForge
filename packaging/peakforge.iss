; Inno Setup 6 script: packs PyInstaller's dist\PeakForge into a Windows installer (per-user, no admin rights needed).
; Build: iscc /DAppVersion=1.0.0 packaging\peakforge.iss        Output: dist\PeakForge-<version>-Setup.exe
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{5E2C7B41-9A3D-4F68-B1E0-3C8D6A92F7D5}
AppName=PeakForge
AppVersion={#AppVersion}
AppVerName=PeakForge {#AppVersion}
AppPublisher=Eggy & Claude
AppPublisherURL=https://github.com/Wiolic/PeakForge
AppSupportURL=https://github.com/Wiolic/PeakForge/issues
AppUpdatesURL=https://github.com/Wiolic/PeakForge/releases
AppCopyright=Copyright (C) 2026 Eggy & Claude. MIT License
VersionInfoVersion={#AppVersion}
VersionInfoProductName=PeakForge
VersionInfoProductVersion={#AppVersion}
VersionInfoCompany=Eggy & Claude
VersionInfoDescription=PeakForge Setup - XPS analysis and peak fitting software
VersionInfoCopyright=Copyright (C) 2026 Eggy & Claude
DefaultDirName={autopf}\PeakForge
DefaultGroupName=PeakForge
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=PeakForge-{#AppVersion}-Setup
SetupIconFile=..\src\peakforge\assets\peakforge.ico
UninstallDisplayIcon={app}\PeakForge.exe
Compression=lzma2/ultra64
LZMAUseSeparateProcess=yes
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\LICENSE
WizardStyle=modern
ChangesAssociations=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; Welcome / finish pages: credit, license, disclaimer, citation (text matches src/peakforge/__init__.py).
; Inno 6 has no official Simplified Chinese language file, so the wizard stays English with a bilingual note.
[Messages]
WelcomeLabel2=This will install [name/ver] on your computer.%n%nDeveloped by Eggy & Claude Opus 5.5 (Anthropic).%nLicense: MIT.%n%nPeakForge is a research aid, provided "as is" without warranty. Fitted results depend on the background, line shapes, constraints and starting values and may be biased: before publishing or drawing conclusions, cross-check against established XPS software (CasaXPS, Thermo Avantage, PHI MultiPak) and judge the results yourself.%n%n本软件由 Eggy 与 Claude Opus 5.5（Anthropic）开发，仅用于科研辅助，按“现状”提供。分峰结果取决于背景、线形、约束与初值，发表前请与常用 XPS 软件比对并自行判断。
FinishedLabel=Setup has finished installing [name] on your computer.%n%nSynthetic demo spectra are in the "examples" folder of the installation (they are used by the beginner tutorial in Help > User guide, F1).%n%nIf you use PeakForge in a publication, please cite it: Eggy & Claude. PeakForge, version {#AppVersion}. https://github.com/Wiolic/PeakForge%n%n论文中使用请引用本软件。

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "assoc"; Description: "Associate .xpsproj project files with PeakForge"; GroupDescription: "File association:"

[Files]
Source: "..\dist\PeakForge\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion createallsubdirs
; synthetic demo data (the tutorial walks through it)
Source: "..\examples\*.csv"; DestDir: "{app}\examples"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\PeakForge"; Filename: "{app}\PeakForge.exe"
Name: "{group}\Uninstall PeakForge"; Filename: "{uninstallexe}"
Name: "{autodesktop}\PeakForge"; Filename: "{app}\PeakForge.exe"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\.xpsproj"; ValueType: string; ValueName: ""; ValueData: "PeakForge.Project"; Flags: uninsdeletevalue; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\PeakForge.Project"; ValueType: string; ValueName: ""; ValueData: "PeakForge project"; Flags: uninsdeletekey; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\PeakForge.Project\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\PeakForge.exe,0"; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\PeakForge.Project\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\PeakForge.exe"" ""%1"""; Tasks: assoc

[Run]
Filename: "{app}\PeakForge.exe"; Description: "{cm:LaunchProgram,PeakForge}"; Flags: nowait postinstall skipifsilent
