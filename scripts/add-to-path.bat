@echo off
setlocal EnableDelayedExpansion
REM Add impact-vision to PATH (Windows CMD)
REM Usage: scripts\add-to-path.bat

for /f "delims=" %%i in ('python -c "import sysconfig; print(sysconfig.get_path('scripts'))"') do set "SCRIPTS_DIR=%%i"

if "!SCRIPTS_DIR!"=="" (
    echo Error: Python not found. Install Python 3.11+ first.
    exit /b 1
)

echo Python Scripts directory: !SCRIPTS_DIR!

REM Check if already on PATH using delayed expansion to handle special chars
echo !PATH! | findstr /i /c:"!SCRIPTS_DIR!" >nul 2>&1
if !errorlevel!==0 (
    echo Already on PATH.
) else (
    REM Use PowerShell to safely modify user PATH without 1024-char limit
    powershell -Command "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';!SCRIPTS_DIR!', 'User')"
    set "PATH=!PATH!;!SCRIPTS_DIR!"
    echo Added to user PATH.
)

echo.
echo ============================================================
echo IMPORTANT: You must RESTART your terminal (close and reopen
echo CMD/PowerShell) for the PATH change to take effect.
echo After restarting, run: impact-vision --help
echo ============================================================
endlocal
