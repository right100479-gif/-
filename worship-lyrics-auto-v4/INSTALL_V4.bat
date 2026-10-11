@echo off
setlocal
cd /d "%~dp0"
title Worship Lyrics Auto 4.0 Installer

echo ============================================================
echo Worship Lyrics Auto 4.0
echo Vocal Separation + Korean CTC Alignment
echo ============================================================
echo.

set "APPDIR=%LOCALAPPDATA%\WorshipLyricsAuto4"
set "VENV=%APPDIR%\.venv"
if not exist "%APPDIR%" mkdir "%APPDIR%"

set "PYEXE="
where py >nul 2>&1
if not errorlevel 1 set "PYEXE=py -3.11"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

if not defined PYEXE (
  where winget >nul 2>&1
  if errorlevel 1 goto :nopython
  echo Installing Python 3.11...
  winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
  if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
  ) else (
    echo Python installation finished. Run INSTALL_V4.bat again.
    pause
    exit /b 0
  )
)

echo [1/5] FFmpeg check...
where ffmpeg >nul 2>&1
if errorlevel 1 (
  where winget >nul 2>&1
  if errorlevel 1 goto :noffmpeg
  winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
)

echo [2/5] Python environment...
if not exist "%VENV%\Scripts\python.exe" (
  %PYEXE% -m venv "%VENV%"
  if errorlevel 1 goto :fail
)

echo [3/5] AI packages...
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail
"%VENV%\Scripts\python.exe" -m pip install whisperx demucs tkinterdnd2
if errorlevel 1 goto :fail

echo [4/5] App files...
copy /Y "WorshipLyricsAuto4.pyw" "%APPDIR%\WorshipLyricsAuto4.pyw" >nul

echo [5/5] VEGAS fade helper...
for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('MyDocuments')"`) do set "DOCS=%%D"
if not defined DOCS set "DOCS=%USERPROFILE%\Documents"
set "VEGASSCRIPTS=%DOCS%\Vegas Script Menu"
if not exist "%VEGASSCRIPTS%" mkdir "%VEGASSCRIPTS%"
copy /Y "Worship_Fade_Imported_Subtitles.cs" "%VEGASSCRIPTS%\Worship_Fade_Imported_Subtitles.cs" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Worship Lyrics Auto 4.0.lnk'); $s.TargetPath='%VENV%\Scripts\pythonw.exe'; $s.Arguments='\"%APPDIR%\WorshipLyricsAuto4.pyw\"'; $s.WorkingDirectory='%APPDIR%'; $s.Save()"

echo.
echo ============================================================
echo INSTALL COMPLETE
echo ============================================================
echo.
echo Desktop shortcut: Worship Lyrics Auto 4.0
echo.
echo In VEGAS: Tools ^> Scripting ^> Rescan Script Menu Folder
echo.
pause
exit /b 0

:nopython
echo ERROR: Python 3.11 is not installed and winget is unavailable.
pause
exit /b 1
:noffmpeg
echo ERROR: FFmpeg is required and winget is unavailable.
pause
exit /b 1
:fail
echo INSTALL FAILED.
pause
exit /b 1
