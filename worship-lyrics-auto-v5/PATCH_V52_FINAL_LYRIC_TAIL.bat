@echo off
setlocal
title Worship Lyrics Auto 5.0 - Final Lyric Tail Patch

set "APPDIR=%LOCALAPPDATA%\WorshipLyricsAuto5"
if not exist "%APPDIR%" mkdir "%APPDIR%"

echo Downloading latest WorshipLyricsAuto5.pyw...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/right100479-gif/-/main/worship-lyrics-auto-v5/WorshipLyricsAuto5.pyw' -OutFile '%APPDIR%\WorshipLyricsAuto5.pyw'; exit 0 } catch { Write-Host $_; exit 1 }"
if errorlevel 1 goto :fail

echo.
echo PATCH COMPLETE
echo The generated CSV/SRT/VEGAS files will now keep the final lyric through the song tail.
echo.
pause
exit /b 0

:fail
echo PATCH FAILED
pause
exit /b 1
