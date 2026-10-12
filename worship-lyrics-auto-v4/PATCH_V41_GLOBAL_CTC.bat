@echo off
setlocal
cd /d "%~dp0"
title Worship Lyrics Auto 4.1 Global CTC Patch

echo ============================================================
echo Worship Lyrics Auto 4.1
echo Full-song Global CTC Alignment Fix
echo ============================================================
echo.

set "APPDIR=%LOCALAPPDATA%\WorshipLyricsAuto4"

if not exist "%APPDIR%\WorshipLyricsAuto4.pyw" (
  echo ERROR: Worship Lyrics Auto 4.0 is not installed.
  echo Run INSTALL_V4_FIXED.bat first.
  pause
  exit /b 1
)

copy /Y "%APPDIR%\WorshipLyricsAuto4.pyw" "%APPDIR%\WorshipLyricsAuto4_backup_before_v41.pyw" >nul
copy /Y "WorshipLyricsAuto4.pyw" "%APPDIR%\WorshipLyricsAuto4.pyw" >nul

if errorlevel 1 (
  echo PATCH FAILED.
  pause
  exit /b 1
)

echo.
echo PATCH COMPLETE
echo.
echo v4.1 removes the unreliable section-window timing.
echo It now aligns ALL lyric lines to the entire separated vocal track
echo in one monotonic Korean CTC pass.
echo.
echo Close the app, reopen it, and regenerate the same song once.
echo Check the first 10 timing lines in the log BEFORE importing to VEGAS.
echo.
pause
