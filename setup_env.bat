@echo off
REM Setup script for ASTM Noise Analysis Tool
REM Run this script to set up the Python environment

echo Setting up ASTM Noise Analysis environment...

REM Change to script directory
cd /d "%~dp0"

REM Define virtual environment location (portable across users)
set VENV_DIR=%USERPROFILE%\Documents\Python Environments
set PROJECT_NAME=astm-noise-analysis
set VENV_PATH=%VENV_DIR%\%PROJECT_NAME%

REM Check if Python is available
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python launcher (py) not found!
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check 'Add Python to PATH' during installation.
    pause
    exit /b 1
)

REM Show Python version
echo Found Python:
py --version

REM Create the Python Environments directory if it doesn't exist
if not exist "%VENV_DIR%" (
    echo Creating Python Environments directory...
    mkdir "%VENV_DIR%"
)

REM Remove existing virtual environment if it exists (both local and centralized)
if exist ".venv" (
    echo Removing local virtual environment...
    rmdir /s /q ".venv"
)
if exist "%VENV_PATH%" (
    echo Removing existing centralized virtual environment...
    rmdir /s /q "%VENV_PATH%"
)

REM Create new virtual environment in centralized location
echo Creating virtual environment at: %VENV_PATH%
py -m venv "%VENV_PATH%"

REM Install packages
echo Installing required packages...
if exist "requirements.txt" (
    "%VENV_PATH%\Scripts\python.exe" -m pip install --upgrade pip
    "%VENV_PATH%\Scripts\python.exe" -m pip install --only-binary :all: -r requirements.txt
    echo Environment setup complete!
    echo Virtual environment created at: %VENV_PATH%
    echo You can now run 'run_astm_noise.bat' to start the application.
) else (
    echo Warning: requirements.txt not found. Installing basic packages...
    "%VENV_PATH%\Scripts\python.exe" -m pip install --upgrade pip
    "%VENV_PATH%\Scripts\python.exe" -m pip install --only-binary :all: numpy matplotlib scipy
    echo Basic setup complete. You may need to install additional packages as needed.
    echo Virtual environment created at: %VENV_PATH%
)

echo.
pause
