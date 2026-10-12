@echo off
setlocal
cd /d "%~dp0"
title Worship Lyrics Auto 5.0 - VEGAS Importer

echo ============================================================
echo Worship Lyrics Auto 5.0
echo VEGAS Direct Subtitle Importer
echo ============================================================
echo.

for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('MyDocuments')"`) do set "DOCS=%%D"
if not defined DOCS set "DOCS=%USERPROFILE%\Documents"
set "VEGASSCRIPTS=%DOCS%\Vegas Script Menu"

if not exist "%VEGASSCRIPTS%" mkdir "%VEGASSCRIPTS%"

copy /Y "Worship_Import_Auto5_Subtitles.cs" "%VEGASSCRIPTS%\Worship_Import_Auto5_Subtitles.cs" >nul
if errorlevel 1 goto :fail

echo.
echo INSTALL COMPLETE
echo VEGAS SCRIPT FOLDER: %VEGASSCRIPTS%
echo.
echo VEGAS:
echo Tools ^> Scripting ^> Rescan Script Menu Folder
echo.
echo Then run:
echo Worship_Import_Auto5_Subtitles
echo.
echo This importer reads *_SYNC_REPORT.csv directly.
echo It does NOT use Insert ^> Insert Subtitles from Files.
echo.
pause
exit /b 0

:fail
echo INSTALL FAILED.
pause
exit /b 1
