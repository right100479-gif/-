@echo off
setlocal
cd /d "%~dp0"
title Worship Lyrics Auto 5.0 Installer

echo ============================================================
echo Worship Lyrics Auto 5.0
echo Demucs + MMS-300M + built-in CTC Viterbi
echo ============================================================
echo.

set "APPDIR=%LOCALAPPDATA%\WorshipLyricsAuto5"
set "VENV=%APPDIR%\.venv"
if not exist "%APPDIR%" mkdir "%APPDIR%"

echo [0/5] Python 3.11 check...
set "PYCMD="

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
  set PYCMD="%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
)
if not defined PYCMD if exist "%ProgramFiles%\Python311\python.exe" (
  set PYCMD="%ProgramFiles%\Python311\python.exe"
)
if not defined PYCMD (
  py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info[:2]==(3,11) else 1)" >nul 2>&1
  if not errorlevel 1 set "PYCMD=py -3.11"
)

if not defined PYCMD (
  echo Python 3.11 runtime was not found.
  where winget >nul 2>&1
  if errorlevel 1 goto :nopython
  echo Installing Python 3.11 with winget...
  winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
  if errorlevel 1 goto :nopython

  if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set PYCMD="%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
  )
  if not defined PYCMD if exist "%ProgramFiles%\Python311\python.exe" (
    set PYCMD="%ProgramFiles%\Python311\python.exe"
  )
  if not defined PYCMD (
    echo Python 3.11 was installed. Close this window and run INSTALL_V5.bat again.
    pause
    exit /b 0
  )
)

echo Python command: %PYCMD%
%PYCMD% --version
if errorlevel 1 goto :nopython

echo [1/5] FFmpeg check...
where ffmpeg >nul 2>&1
if errorlevel 1 (
  where winget >nul 2>&1
  if errorlevel 1 goto :noffmpeg
  winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
  if errorlevel 1 goto :noffmpeg
)

echo [2/5] Python environment...
if not exist "%VENV%\Scripts\python.exe" (
  %PYCMD% -m venv "%VENV%"
  if errorlevel 1 goto :fail
)

echo [3/5] AI packages...
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :fail
"%VENV%\Scripts\python.exe" -m pip install torch demucs "transformers>=4.34" uroman numpy tkinterdnd2
if errorlevel 1 goto :fail

echo [4/5] App files...
copy /Y "WorshipLyricsAuto5.pyw" "%APPDIR%\WorshipLyricsAuto5.pyw" >nul
if errorlevel 1 goto :fail

echo [5/5] VEGAS fade helper and desktop shortcut...
for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('MyDocuments')"`) do set "DOCS=%%D"
if not defined DOCS set "DOCS=%USERPROFILE%\Documents"
set "VEGASSCRIPTS=%DOCS%\Vegas Script Menu"
if not exist "%VEGASSCRIPTS%" mkdir "%VEGASSCRIPTS%"
copy /Y "Worship_Fade_Imported_Subtitles.cs" "%VEGASSCRIPTS%\Worship_Fade_Imported_Subtitles.cs" >nul\r\ncopy /Y "Worship_Import_Auto5_Subtitles.cs" "%VEGASSCRIPTS%\Worship_Import_Auto5_Subtitles.cs" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Worship Lyrics Auto 5.0.lnk'); $s.TargetPath='%VENV%\Scripts\pythonw.exe'; $s.Arguments='\"%APPDIR%\WorshipLyricsAuto5.pyw\"'; $s.WorkingDirectory='%APPDIR%'; $s.Save()"

echo.
echo ============================================================
echo INSTALL COMPLETE
echo Desktop: Worship Lyrics Auto 5.0
echo ============================================================
echo.
echo First analysis downloads the MMS alignment model.
echo It can take a while. This is normal.
echo.
pause
exit /b 0

:nopython
echo ERROR: Python 3.11 could not be found or installed.
pause
exit /b 1

:noffmpeg
echo ERROR: FFmpeg could not be found or installed.
echo If winget installed FFmpeg just now, close this window and run again.
pause
exit /b 1

:fail
echo INSTALL FAILED.
pause
exit /b 1
