#define AutoTapInstaller
[Setup]
AppName=AutoTap
AppVersion=2.0.0
AppPublisher=AutoTap
AppPublisherURL=https://github.com/ABUGG-007/AutoTap
AppSupportURL=https://github.com/ABUGG-007/AutoTap
DefaultDirName={autopf}\AutoTap
DefaultGroupName=AutoTap
OutputBaseFilename=AutoTap_2.0.0_Setup
OutputDir=dist
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\AutoTap.exe
SetupIconFile=icon.ico
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"

[Files]
Source: "dist\AutoTap\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\AutoTap"; Filename: "{app}\AutoTap.exe"
Name: "{group}\卸载 AutoTap"; Filename: "{uninstallexe}"
Name: "{autodesktop}\AutoTap"; Filename: "{app}\AutoTap.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AutoTap.exe"; Description: "启动 AutoTap"; Flags: nowait postinstall skipifsilent
