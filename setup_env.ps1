# Setup script for ASTM Noise Analysis Tool
# Run this script to set up the Python environment

Write-Host "Setting up ASTM Noise Analysis environment..." -ForegroundColor Green

# Change to script directory
Set-Location -Path $PSScriptRoot

# Define virtual environment location (portable across users)
# Using Documents folder outside OneDrive to avoid syncing conflicts
$venvDir = Join-Path $env:USERPROFILE "Documents\Python Environments"
$projectName = "astm-noise-analysis"
$venvPath = Join-Path $venvDir $projectName

# Check if Python is available
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Python launcher (py) not found!" -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Yellow
    exit 1
}

# Show Python version
Write-Host "Found Python: " -NoNewline -ForegroundColor Gray
py --version

# Create the Python Environments directory if it doesn't exist
if (-not (Test-Path $venvDir)) {
    Write-Host "Creating Python Environments directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $venvDir -Force | Out-Null
}

# Remove existing virtual environment if it exists (both local and centralized)
if (Test-Path ".venv") {
    Write-Host "Removing local virtual environment..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force .venv
}
if (Test-Path $venvPath) {
    Write-Host "Removing existing centralized virtual environment..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $venvPath
}

# Create new virtual environment in centralized location
Write-Host "Creating virtual environment at: $venvPath" -ForegroundColor Green
py -m venv $venvPath

# Install packages
Write-Host "Installing required packages..." -ForegroundColor Green
$pythonExe = Join-Path $venvPath "Scripts\python.exe"
if (Test-Path "requirements.txt") {
    & $pythonExe -m pip install --upgrade pip
    & $pythonExe -m pip install --only-binary :all: -r requirements.txt
    Write-Host "Environment setup complete!" -ForegroundColor Green
    Write-Host "Virtual environment created at: $venvPath" -ForegroundColor Cyan
    Write-Host "You can now run 'run_astm_noise.ps1' to start the application." -ForegroundColor Cyan
} else {
    Write-Host "Warning: requirements.txt not found. Installing basic packages..." -ForegroundColor Yellow
    & $pythonExe -m pip install --upgrade pip
    & $pythonExe -m pip install --only-binary :all: numpy matplotlib scipy
    Write-Host "Basic setup complete. You may need to install additional packages as needed." -ForegroundColor Yellow
    Write-Host "Virtual environment created at: $venvPath" -ForegroundColor Cyan
}

Write-Host "`nPress any key to continue..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
