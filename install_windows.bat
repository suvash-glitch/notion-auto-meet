@echo off
REM ============================================================
REM  Notion Auto-Meet — Quick Windows Installer (no build tools)
REM
REM  This is a lightweight alternative to the full installer.
REM  It installs the Python script directly with autostart.
REM
REM  Prerequisites: Python 3.8+ with pip
REM ============================================================

setlocal

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo.
echo ============================================
echo  Notion Auto-Meet — Quick Install
echo ============================================
echo.

REM --- Check Python ---
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.8+ from python.org
    pause
    exit /b 1
)

REM --- Install dependencies ---
echo [1/3] Installing Python dependencies...
pip install numpy pyautogui mss >nul 2>&1
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)
echo       Done.

REM --- Create a VBS launcher (runs without console window) ---
echo [2/3] Creating silent launcher...
set "PYTHON_EXE="
for /f "delims=" %%i in ('where pythonw 2^>nul') do set "PYTHON_EXE=%%i"
if "%PYTHON_EXE%"=="" (
    for /f "delims=" %%i in ('where python') do set "PYTHON_EXE=%%i"
)

set "VBS_PATH=%PROJECT_DIR%run_hidden.vbs"
(
    echo Set WshShell = CreateObject^("WScript.Shell"^)
    echo WshShell.Run """%PYTHON_EXE%"" ""%PROJECT_DIR%main.py""", 0, False
) > "%VBS_PATH%"
echo       Done.

REM --- Add to startup ---
echo [3/3] Adding to Windows startup...
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%STARTUP_DIR%\NotionAutoMeet.vbs"

copy /y "%VBS_PATH%" "%SHORTCUT%" >nul 2>&1
if errorlevel 1 (
    echo WARNING: Could not copy to Startup folder.
    echo          You can manually copy run_hidden.vbs to:
    echo          %STARTUP_DIR%
) else (
    echo       Done. Added to Startup folder.
)

echo.
echo ============================================
echo  Installation complete!
echo.
echo  Notion Auto-Meet will start automatically
echo  when you log in to Windows.
echo.
echo  Starting now...
echo ============================================
echo.

REM --- Start it now ---
wscript "%VBS_PATH%"

echo  Running in background. Check notion-auto-meet.log for activity.
echo.
echo  To uninstall, run: uninstall_windows.bat
echo.
pause
