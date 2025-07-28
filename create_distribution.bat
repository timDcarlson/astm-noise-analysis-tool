@echo off
REM Simple batch script to create distribution package

echo ASTM Noise Analysis Tool - Distribution Creator
echo ===============================================
echo.

set VERSION=2.1.0
set PACKAGE_NAME=ASTM-Noise-Analysis-Tool-v%VERSION%

echo Creating distribution package v%VERSION%...
echo.

REM Check if PowerShell is available (preferred method)
powershell -Command "Get-Host" >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo Using PowerShell for package creation...
    powershell -ExecutionPolicy Bypass -File "create_distribution.ps1" -Version %VERSION%
    goto :end
)

REM Fallback: Basic file copying without PowerShell
echo PowerShell not available, using basic file copying...
echo.

REM Create package directory
if exist "%PACKAGE_NAME%" rmdir /s /q "%PACKAGE_NAME%"
mkdir "%PACKAGE_NAME%"

REM Copy essential files
echo Copying files...
copy "*.py" "%PACKAGE_NAME%\" >nul 2>&1
copy "*.bat" "%PACKAGE_NAME%\" >nul 2>&1
copy "*.ps1" "%PACKAGE_NAME%\" >nul 2>&1
copy "*.txt" "%PACKAGE_NAME%\" >nul 2>&1
copy "*.md" "%PACKAGE_NAME%\" >nul 2>&1

echo Files copied to %PACKAGE_NAME%\
echo.
echo To create a ZIP file, manually compress the %PACKAGE_NAME% folder
echo or run: powershell "Compress-Archive -Path '%PACKAGE_NAME%' -DestinationPath '%PACKAGE_NAME%.zip'"

:end
echo.
echo Package creation complete!
pause
