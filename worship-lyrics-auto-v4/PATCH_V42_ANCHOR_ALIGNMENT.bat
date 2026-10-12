@echo off
setlocal
cd /d "%~dp0"
title Worship Lyrics Auto 4.2 Anchor Alignment Patch

echo ============================================================
echo Worship Lyrics Auto 4.2
echo VEGAS Section Anchors + Short-window CTC
echo ============================================================
echo.

set "APPDIR=%LOCALAPPDATA%\WorshipLyricsAuto4"

if not exist "%APPDIR%\WorshipLyricsAuto4.pyw" (
  echo ERROR: Worship Lyrics Auto 4.x is not installed.
  pause
  exit /b 1
)

copy /Y "%APPDIR%\WorshipLyricsAuto4.pyw" "%APPDIR%\WorshipLyricsAuto4_backup_before_v42.pyw" >nul
copy /Y "WorshipLyricsAuto4.pyw" "%APPDIR%\WorshipLyricsAuto4.pyw" >nul
if errorlevel 1 goto :fail

for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('MyDocuments')"`) do set "DOCS=%%D"
if not defined DOCS set "DOCS=%USERPROFILE%\Documents"
set "VEGASSCRIPTS=%DOCS%\Vegas Script Menu"
if not exist "%VEGASSCRIPTS%" mkdir "%VEGASSCRIPTS%"

copy /Y "Worship_Export_Section_Anchors.cs" "%VEGASSCRIPTS%\Worship_Export_Section_Anchors.cs" >nul
copy /Y "Worship_Fade_Imported_Subtitles.cs" "%VEGASSCRIPTS%\Worship_Fade_Imported_Subtitles.cs" >nul

echo.
echo PATCH COMPLETE
echo.
echo In VEGAS:
echo Tools ^> Scripting ^> Rescan Script Menu Folder
echo.
echo Then put EXACTLY 9 timeline markers at the first sung word of:
echo 1 Verse 1
echo 2 Verse 2
echo 3 Chorus 1
echo 4 Verse 3
echo 5 Chorus 2
echo 6 Bridge
echo 7 Final Chorus 1
echo 8 Final Chorus 2
echo 9 Outro
echo.
echo Run Worship_Export_Section_Anchors.
echo Then regenerate the song in Worship Lyrics Auto 4.2.
echo.
pause
exit /b 0

:fail
echo PATCH FAILED.
pause
exit /b 1
