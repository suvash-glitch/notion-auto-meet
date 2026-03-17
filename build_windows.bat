@echo off
REM ============================================================
REM  Notion Auto-Meet — Build standalone Windows .exe
REM
REM  Prerequisite: Python 3.8+ with pip (only on the BUILD machine)
REM  End users do NOT need Python — the .exe is fully self-contained.
REM
REM  Output: dist\NotionAutoMeet.exe
REM ============================================================

setlocal enabledelayedexpansion

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo.
echo  ================================================
echo   Notion Auto-Meet — Build Windows .exe
echo  ================================================
echo.

REM --- Check Python ---
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found. Install Python 3.8+ from python.org
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  [OK] %%v

REM --- Install build dependencies ---
echo.
echo  [1/3] Installing dependencies...
pip install --quiet pyinstaller numpy pyautogui mss Pillow
if errorlevel 1 (
    echo  ERROR: pip install failed.
    pause
    exit /b 1
)
echo        Done.

REM --- Generate icon ---
echo  [2/3] Generating icon...
if not exist "installer\icon.ico" (
    python installer\create_icon.py
    if errorlevel 1 (
        echo        Skipping icon (Pillow issue). Building without it.
    )
) else (
    echo        Already exists.
)

REM --- Build with PyInstaller ---
echo  [3/3] Packaging with PyInstaller...

set "ICON_FLAG="
if exist "installer\icon.ico" set "ICON_FLAG=--icon installer\icon.ico"

pyinstaller ^
    --noconfirm ^
    --onefile ^
    --noconsole ^
    --name "NotionAutoMeet" ^
    !ICON_FLAG! ^
    --hidden-import mss.windows ^
    --hidden-import ctypes.wintypes ^
    --exclude-module Quartz ^
    --exclude-module AppKit ^
    --exclude-module Foundation ^
    main.py

if errorlevel 1 (
    echo.
    echo  ERROR: Build failed. See output above.
    pause
    exit /b 1
)

if not exist "dist\NotionAutoMeet.exe" (
    echo  ERROR: Output not found.
    pause
    exit /b 1
)

for %%A in ("dist\NotionAutoMeet.exe") do set "SIZE=%%~zA"
set /a MB=!SIZE! / 1048576

echo.
echo  ================================================
echo   Build complete!
echo.
echo   dist\NotionAutoMeet.exe  (!MB! MB)
echo.
echo   This single file is all you need to distribute.
echo   Users just double-click it — no Python, no install.
echo   First run auto-registers for Windows startup.
echo   To uninstall: NotionAutoMeet.exe --uninstall
echo  ================================================
echo.
pause
