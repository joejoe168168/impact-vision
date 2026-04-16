@echo off
REM Add impact-vision to PATH (Windows CMD)
REM Usage: scripts\add-to-path.bat

for /f "delims=" %%i in ('python -c "import sysconfig; print(sysconfig.get_path('scripts'))"') do set SCRIPTS_DIR=%%i

if "%SCRIPTS_DIR%"=="" (
    echo Error: Python not found. Install Python 3.11+ first.
    exit /b 1
)

echo %PATH% | findstr /i "%SCRIPTS_DIR%" >nul
if %errorlevel%==0 (
    echo Already on PATH: %SCRIPTS_DIR%
) else (
    setx PATH "%PATH%;%SCRIPTS_DIR%" >nul
    set PATH=%PATH%;%SCRIPTS_DIR%
    echo Added to PATH: %SCRIPTS_DIR%
)

echo.
where impact-vision >nul 2>&1
if %errorlevel%==0 (
    echo impact-vision is ready! Try: impact-vision --help
) else (
    echo Please restart your terminal, then run: impact-vision --help
)
