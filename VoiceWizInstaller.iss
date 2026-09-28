#define MyAppName "VoiceWiz"
#define MyAppVersion "1.0"
#define MyAppPublisher "VoiceWiz"
#define MyAppURL "https://github.com"
#define MyAppExeName "VoiceWiz.bat"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=E:\VoiceWiz\installer_output
OutputBaseFilename=VoiceWiz_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
SetupIconFile=E:\VoiceWiz\voicewiz.ico
UninstallDisplayName=VoiceWiz

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "E:\VoiceWiz\voicewiz.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\VoiceWiz\training.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\VoiceWiz\conversion.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\VoiceWiz\VoiceWiz.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\VoiceWiz\setup.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\VoiceWiz\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\VoiceWiz\README.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "E:\VoiceWiz\voicewiz.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\VoiceWiz\python-3.12.0-amd64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Dirs]
Name: "{app}\profiles"
Name: "{app}\voices"
Name: "{app}\temp"
Name: "{app}\assets"

[Icons]
Name: "{group}\VoiceWiz"; Filename: "{app}\VoiceWiz.bat"; IconFilename: "{app}\voicewiz.ico"
Name: "{group}\{cm:UninstallProgram,VoiceWiz}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\VoiceWiz"; Filename: "{app}\VoiceWiz.bat"; IconFilename: "{app}\voicewiz.ico"; Tasks: desktopicon

[Run]
Filename: "{tmp}\python-3.12.0-amd64.exe"; Parameters: "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0"; StatusMsg: "Installing Python 3.12..."; Check: not PythonInstalled; Flags: waituntilterminated

[Code]
var
  ProgressPage: TOutputProgressWizardPage;

function PythonInstalled: Boolean;
begin
  Result := RegKeyExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\Python\PythonCore\3.12');
  if not Result then
    Result := RegKeyExists(HKEY_CURRENT_USER, 'SOFTWARE\Python\PythonCore\3.12');
end;

procedure RunPip(AppDir: String; Params: String; StepText: String; StepNum: Integer; TotalSteps: Integer);
var
  PipExe: String;
  ResultCode: Integer;
begin
  PipExe := AppDir + '\venv\Scripts\pip.exe';
  ProgressPage.SetText(StepText, '');
  ProgressPage.SetProgress(StepNum, TotalSteps);
  Exec(PipExe, Params, AppDir, SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  AppDir: String;
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    AppDir := ExpandConstant('{app}');

    ProgressPage := CreateOutputProgressPage(
      'Setting Up VoiceWiz',
      'Installing required components. Please wait...'
    );
    ProgressPage.Show;

    try
      // Step 1: Create venv
      ProgressPage.SetText('Creating Python environment...', '');
      ProgressPage.SetProgress(1, 10);
      Exec('python', '-m venv "' + AppDir + '\venv"', AppDir, SW_HIDE, ewWaitUntilTerminated, ResultCode);

      // Step 2: numpy first
      RunPip(AppDir, 'install numpy==1.26.4 --quiet', 'Installing numpy...', 2, 10);

      // Step 3: torch CPU
      RunPip(AppDir,
        'install torch==2.4.0+cpu torchaudio==2.4.0+cpu --index-url https://download.pytorch.org/whl/cpu --quiet',
        'Installing PyTorch (CPU) — largest download, please wait...', 3, 10);

      // Step 4: scipy + librosa
      RunPip(AppDir,
        'install scipy==1.13.1 librosa==0.10.2 soundfile sounddevice pydub --quiet',
        'Installing audio libraries...', 4, 10);

      // Step 5: UI
      RunPip(AppDir,
        'install customtkinter Pillow --quiet',
        'Installing UI libraries...', 5, 10);

      // Step 6: voice tools
      RunPip(AppDir,
        'install munch==4.0.0 einops==0.8.0 praat-parselmouth pyworld resemblyzer --quiet',
        'Installing voice processing tools...', 6, 10);

      // Step 7: AI
      RunPip(AppDir,
        'install descript-audio-codec transformers==4.46.3 huggingface-hub --quiet',
        'Installing AI libraries...', 7, 10);

      // Step 8: seed-vc
      ProgressPage.SetText('Cloning voice engine (seed-vc)...', '');
      ProgressPage.SetProgress(8, 10);
      Exec('git', 'clone https://github.com/Plachtaa/seed-vc.git "' + AppDir + '\seed-vc"',
        AppDir, SW_HIDE, ewWaitUntilTerminated, ResultCode);

      // Step 9: lock numpy
      RunPip(AppDir,
        'install numpy==1.26.4 --force-reinstall --no-deps --quiet',
        'Locking numpy version...', 9, 10);

      // Done
      ProgressPage.SetText('Setup complete!', '');
      ProgressPage.SetProgress(10, 10);

    finally
      ProgressPage.Hide;
    end;
  end;
end;