@echo off
setlocal
cd /d "%~dp0"
title Worship Lyrics Auto 5.1 - VEGAS Importer

echo ============================================================
echo Worship Lyrics Auto 5.1
echo VEGAS Direct Subtitle Importer
echo ============================================================
echo.

for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('MyDocuments')"`) do set "DOCS=%%D"
if not defined DOCS set "DOCS=%USERPROFILE%\Documents"
set "VEGASSCRIPTS=%DOCS%\Vegas Script Menu"

if not exist "%VEGASSCRIPTS%" mkdir "%VEGASSCRIPTS%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/right100479-gif/-/main/worship-lyrics-auto-v5/Worship_Import_Auto5_1_Subtitles.cs' -OutFile '%VEGASSCRIPTS%\Worship_Import_Auto5_1_Subtitles.cs'; exit 0 } catch { Write-Host $_; exit 1 }"
if errorlevel 1 goto :fail

if not exist "%VEGASSCRIPTS%\Worship_Import_Auto5_1_Subtitles.cs" goto :fail

echo.
echo INSTALL COMPLETE
echo VEGAS SCRIPT FOLDER: %VEGASSCRIPTS%
echo INSTALLED: Worship_Import_Auto5_1_Subtitles.cs
echo.
echo In VEGAS:
echo Tools ^> Scripting ^> Rescan Script Menu Folder
echo Then run: Worship_Import_Auto5_1_Subtitles
echo.
pause
exit /b 0

:fail
echo.
echo INSTALL FAILED - latest 5.1 script was not downloaded.
echo Do not use the old Auto5 script.
pause
exit /b 1
