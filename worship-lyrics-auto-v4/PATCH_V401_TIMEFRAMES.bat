@echo off
setlocal
cd /d "%~dp0"
title Worship Lyrics Auto 4.0.1 TimeFrames Fix

echo ============================================================
echo Worship Lyrics Auto 4.0.1
echo VEGAS Time ^& Frames format fix
echo ============================================================
echo.

set "APPDIR=%LOCALAPPDATA%\WorshipLyricsAuto4"

if not exist "%APPDIR%\WorshipLyricsAuto4.pyw" (
  echo ERROR: Worship Lyrics Auto 4.0 installation was not found.
  echo Run INSTALL_V4_FIXED.bat first.
  pause
  exit /b 1
)

copy /Y "%APPDIR%\WorshipLyricsAuto4.pyw" "%APPDIR%\WorshipLyricsAuto4_backup_before_TimeFrames.pyw" >nul
copy /Y "WorshipLyricsAuto4.pyw" "%APPDIR%\WorshipLyricsAuto4.pyw" >nul

if errorlevel 1 (
  echo PATCH FAILED.
  pause
  exit /b 1
)

echo.
echo PATCH COMPLETE
echo.
echo This fixes VEGAS Time ^& Frames formatting:
echo OLD: 00:00:36:00
echo NEW: 00:00:36.00
echo.
echo Close and reopen Worship Lyrics Auto 4.0.
echo Regenerate the song once.
echo Then import the file named:
echo *_VEGAS_TimeFrames_30fps.txt
echo.
pause
