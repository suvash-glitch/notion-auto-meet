@echo off
REM ============================================================
REM  Notion Auto-Meet — Windows Uninstaller
REM ============================================================

setlocal

echo.
echo ============================================
echo  Notion Auto-Meet — Uninstall
echo ============================================
echo.

REM --- Stop running instances ---
echo Stopping Notion Auto-Meet...
taskkill /F /IM pythonw.exe /FI "WINDOWTITLE eq notion*" >nul 2>&1
taskkill /F /IM NotionAutoMeet.exe >nul 2>&1

REM --- Remove from Startup folder ---
set "SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\NotionAutoMeet.vbs"
if exist "%SHORTCUT%" (
    del "%SHORTCUT%"
    echo Removed from Startup folder.
) else (
    echo Not found in Startup folder.
)

REM --- Remove registry autostart entry ---
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "NotionAutoMeet" /f >nul 2>&1
echo Removed registry autostart entry (if any).

REM --- Remove scheduled task (if any) ---
schtasks /Delete /TN "NotionAutoMeet" /F >nul 2>&1
echo Removed scheduled task (if any).

echo.
echo ============================================
echo  Uninstall complete.
echo  Project files remain in: %~dp0
echo ============================================
echo.
pause
