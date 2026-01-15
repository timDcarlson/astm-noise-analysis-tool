@echo off
REM Launcher for ASTM Noise Analysis Tool

echo Starting ASTM Noise Analysis Tool...

REM Change to script directory
cd /d "%~dp0"

REM Try to use the virtual environment if it exists
set LOCAL_VENV=.venv\Scripts\python.exe
set CENTRAL_VENV_DIR=%USERPROFILE%\Documents\Python Environments
set PROJECT_NAME=astm-noise-analysis
set CENTRAL_VENV=%CENTRAL_VENV_DIR%\%PROJECT_NAME%\Scripts\python.exe

if exist "%CENTRAL_VENV%" (
    echo Using centralized virtual environment...
    echo Python executable: %CENTRAL_VENV%
    "%CENTRAL_VENV%" ASTMnoise.py
) else if exist "%LOCAL_VENV%" (
    echo Using local virtual environment...
    echo Python executable: %LOCAL_VENV%
    "%LOCAL_VENV%" ASTMnoise.py
) else (
    REM Check if py launcher is available
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo Using Python launcher (py)...
        py ASTMnoise.py
    ) else (
        REM Check if python command is available
        python --version >nul 2>&1
        if %errorlevel% equ 0 (
            echo Using system Python...
            python ASTMnoise.py
        ) else (
            echo Error: No Python executable found!
            echo Please ensure Python is installed and accessible.
            echo Or run 'setup_env.bat' to create a virtual environment.
        )
    )
)

echo.
pause
