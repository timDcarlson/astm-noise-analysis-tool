@echo off
setlocal enabledelayedexpansion
REM Setup script for ASTM Noise Analysis Tool
REM Run this script to set up the Python environment

echo Setting up ASTM Noise Analysis environment...

REM Change to script directory
cd /d "%~dp0"

REM Define virtual environment location (portable across users)
set VENV_DIR=%USERPROFILE%\Documents\Python Environments
set PROJECT_NAME=astm-noise-analysis
set VENV_PATH=%VENV_DIR%\%PROJECT_NAME%

REM Find a working Python installation
echo Looking for Python installation...
set PYTHON_CMD=
set IS_WINDOWS_STORE=0

REM Try py launcher first
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    where py | findstr /i "WindowsApps" >nul 2>&1
    if %errorlevel% equ 0 set IS_WINDOWS_STORE=1
    goto :python_found
)

REM Try python3
python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3
    where python3 | findstr /i "WindowsApps" >nul 2>&1
    if %errorlevel% equ 0 set IS_WINDOWS_STORE=1
    goto :python_found
)

REM Try python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    where python | findstr /i "WindowsApps" >nul 2>&1
    if %errorlevel% equ 0 set IS_WINDOWS_STORE=1
    goto :python_found
)

REM No Python found
echo Error: No working Python installation found!
echo.
echo Please install Python from one of these sources:
echo   1. Python.org: https://www.python.org/downloads/
echo   2. Microsoft Store: search for 'Python 3.12' or 'Python 3.11'
echo.
echo Make sure to check 'Add Python to PATH' during installation (python.org)
pause
exit /b 1

:python_found
echo Found Python:
%PYTHON_CMD% --version
if %IS_WINDOWS_STORE% equ 1 (
    echo   Source: Microsoft Store
    echo   Note: Windows Store Python detected. Using compatible installation method.
) else (
    echo   Source: Standard Python installation
)

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
%PYTHON_CMD% -m venv "%VENV_PATH%"

if %errorlevel% neq 0 (
    echo Error creating virtual environment!
    if %IS_WINDOWS_STORE% equ 1 (
        echo.
        echo Windows Store Python may have limitations. Consider:
        echo   1. Installing Python from python.org instead
        echo   2. Or try running: %PYTHON_CMD% -m pip install --user virtualenv
    )
    pause
    exit /b 1
)

REM Verify virtual environment was created
if not exist "%VENV_PATH%\Scripts\python.exe" (
    echo Error: Virtual environment creation failed - python.exe not found
    pause
    exit /b 1
)

REM Install packages
echo Installing required packages...
set VENV_PYTHON=%VENV_PATH%\Scripts\python.exe

REM Upgrade pip
echo   Upgrading pip...
"%VENV_PYTHON%" -m pip install --upgrade pip >nul 2>&1

if exist "requirements.txt" (
<<<<<<< HEAD
    echo   Installing packages from requirements.txt...
    
    REM Try with wheels first
    "%VENV_PYTHON%" -m pip install --only-binary :all: -r requirements.txt >nul 2>&1
    if %errorlevel% equ 0 (
        goto :install_success
    )
    
    REM Fallback: Allow source builds
    echo   Wheel-only installation failed, trying with compilation allowed...
    "%VENV_PYTHON%" -m pip install -r requirements.txt
    if %errorlevel% equ 0 (
        echo   Note: Some packages were built from source (this is normal)
        goto :install_success
    )
    
    REM If that fails, try one by one
    echo   Error: Batch installation failed. Trying packages individually...
    set INSTALL_FAILED=0
    for /f "tokens=*" %%a in (requirements.txt) do (
        set LINE=%%a
        REM Skip empty lines and comments
        if not "!LINE!"=="" (
            echo !LINE! | findstr /b /c:"#" >nul
            if errorlevel 1 (
                echo     Installing %%a...
                "%VENV_PYTHON%" -m pip install %%a >nul 2>&1
                if errorlevel 1 (
                    echo       Failed: %%a
                    set INSTALL_FAILED=1
                )
            )
        )
    )
    if %INSTALL_FAILED% equ 1 (
        goto :install_partial
    )
    goto :install_success
) else (
    REM No requirements.txt - install basic packages
    echo   Warning: requirements.txt not found. Installing basic packages...
    "%VENV_PYTHON%" -m pip install numpy matplotlib scipy
    goto :install_success
=======
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
>>>>>>> 68e894c7f1ad82673a4945626a0c35375333bc91
)

:install_success
echo.
echo Environment setup complete!
echo Virtual environment created at: %VENV_PATH%
echo You can now run 'run_astm_noise.bat' to start the application.
goto :end

:install_partial
echo.
echo Setup completed with errors!
echo Virtual environment created at: %VENV_PATH%
echo You may need to manually install missing packages.
if %IS_WINDOWS_STORE% equ 1 (
    echo.
    echo Windows Store Python Note:
    echo   Consider installing Python from python.org for better compatibility.
)
goto :end

:end
echo.
pause
