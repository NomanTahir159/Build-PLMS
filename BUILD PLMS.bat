@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title PLMS Desktop 0.2.10 - Cargo Windows Builder
color 0A

echo ============================================================
echo        PLMS DESKTOP 0.2.10 - CARGO WINDOWS BUILDER
echo ============================================================
echo.
echo Node.js is optional for frontend verification; npm / npx are not used.
echo It builds PLMS directly with Rust + Tauri.
echo.

if not exist "%~dp0BUILD-WINDOWS.ps1" (
    color 0C
    echo [ERROR] BUILD-WINDOWS.ps1 is missing.
    echo.
    pause
    exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0BUILD-WINDOWS.ps1"
set "BUILD_RESULT=%ERRORLEVEL%"

echo.
if not "%BUILD_RESULT%"=="0" (
    color 0C
    echo ============================================================
    echo                      BUILD FAILED
    echo ============================================================
    echo.
    echo Send me a screenshot of the FIRST red/error section above.
    echo.
    pause
    exit /b %BUILD_RESULT%
)

echo ============================================================
echo                    BUILD COMPLETE
echo ============================================================
echo.

if exist "%~dp0src-tauri\target\release\bundle\nsis" (
    echo Opening the installer folder...
    start "" "%~dp0src-tauri\target\release\bundle\nsis"
) else (
    color 0C
    echo [ERROR] Installer output folder is missing.
    pause
    exit /b 1
)

echo.
pause
exit /b 0
