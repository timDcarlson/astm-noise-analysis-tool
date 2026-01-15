@echo off
REM Quick setup script for ASTM Noise Analysis Tool
REM This is a simplified version of setup_env.bat for easy double-click execution

echo Setting up ASTM Noise Analysis Tool...
echo.

REM Check if setup_env.bat exists and run it
if exist "setup_env.bat" (
    echo Running full setup...
    call setup_env.bat
) else (
    echo Error: setup_env.bat not found!
    echo Please ensure all files are in the same folder.
    pause
    exit /b 1
)

echo.
echo Setup complete! You can now run the tool using run_astm_noise.bat
echo.
pause
