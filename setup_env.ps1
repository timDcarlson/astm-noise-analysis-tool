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

# Function to find a working Python installation
function Find-Python {
    $pythonCommands = @('py', 'python3', 'python')
    
    foreach ($cmd in $pythonCommands) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            try {
                $version = & $cmd --version 2>&1
                if ($LASTEXITCODE -eq 0) {
                    # Check if it's Windows Store Python (has limitations)
                    $pythonPath = (Get-Command $cmd).Source
                    $isWindowsStore = $pythonPath -like "*WindowsApps*"
                    
                    return @{
                        Command = $cmd
                        Version = $version
                        IsWindowsStore = $isWindowsStore
                        Path = $pythonPath
                    }
                }
            } catch {
                continue
            }
        }
    }
    return $null
}

# Find Python installation
Write-Host "Looking for Python installation..." -ForegroundColor Yellow
$python = Find-Python

if (-not $python) {
    Write-Host "Error: No working Python installation found!" -ForegroundColor Red
    Write-Host "`nPlease install Python from one of these sources:" -ForegroundColor Yellow
    Write-Host "  1. Python.org: https://www.python.org/downloads/" -ForegroundColor Cyan
    Write-Host "  2. Microsoft Store: search for 'Python 3.12' or 'Python 3.11'" -ForegroundColor Cyan
    Write-Host "`nMake sure to check 'Add Python to PATH' during installation (python.org)" -ForegroundColor Yellow
    exit 1
}

# Show Python information
Write-Host "Found Python: $($python.Version)" -ForegroundColor Gray
if ($python.IsWindowsStore) {
    Write-Host "  Source: Microsoft Store" -ForegroundColor Gray
    Write-Host "  Note: Windows Store Python detected. Using compatible installation method." -ForegroundColor Yellow
} else {
    Write-Host "  Source: Standard Python installation" -ForegroundColor Gray
}

$pythonCmd = $python.Command

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

try {
    & $pythonCmd -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        throw "venv creation failed with exit code $LASTEXITCODE"
    }
} catch {
    Write-Host "Error creating virtual environment: $_" -ForegroundColor Red
    
    # For Windows Store Python, suggest alternative
    if ($python.IsWindowsStore) {
        Write-Host "`nWindows Store Python may have limitations. Consider:" -ForegroundColor Yellow
        Write-Host "  1. Installing Python from python.org instead" -ForegroundColor Cyan
        Write-Host "  2. Or try running: $pythonCmd -m pip install --user virtualenv" -ForegroundColor Cyan
    }
    exit 1
}

# Verify virtual environment was created
$pythonExe = Join-Path $venvPath "Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Host "Error: Virtual environment creation failed - python.exe not found" -ForegroundColor Red
    exit 1
}

# Install packages
Write-Host "Installing required packages..." -ForegroundColor Green
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> 206fc0808214fdd361282a3921544468223baef1

# Function to install packages with fallback methods
function Install-Packages {
    param (
        [string]$PythonExe,
        [bool]$IsWindowsStore
    )
    
    # First, upgrade pip
    Write-Host "  Upgrading pip..." -ForegroundColor Gray
    try {
        & $PythonExe -m pip install --upgrade pip 2>&1 | Out-Null
    } catch {
        Write-Host "  Warning: Could not upgrade pip, continuing with existing version..." -ForegroundColor Yellow
    }
    
    if (Test-Path "requirements.txt") {
        Write-Host "  Installing packages from requirements.txt..." -ForegroundColor Gray
        
        # Try with wheels first (fastest and most compatible)
        try {
            & $PythonExe -m pip install --only-binary :all: -r requirements.txt
            if ($LASTEXITCODE -eq 0) {
                return $true
            }
        } catch {
            Write-Host "  Wheel-only installation failed, trying with compilation allowed..." -ForegroundColor Yellow
        }
        
        # Fallback: Allow source builds if wheels fail
        try {
            & $PythonExe -m pip install -r requirements.txt
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  Note: Some packages were built from source (this is normal)" -ForegroundColor Yellow
                return $true
            }
        } catch {
            Write-Host "  Package installation failed: $_" -ForegroundColor Red
            return $false
        }
        
        # If we get here, installation failed
        Write-Host "  Error: Could not install packages from requirements.txt" -ForegroundColor Red
        
        # Try installing packages one by one to identify problems
        Write-Host "  Attempting to install packages individually..." -ForegroundColor Yellow
        $failed = @()
        Get-Content "requirements.txt" | ForEach-Object {
            $pkg = $_.Trim()
            if ($pkg -and -not $pkg.StartsWith('#')) {
                Write-Host "    Installing $pkg..." -ForegroundColor Gray
                try {
                    & $PythonExe -m pip install $pkg 2>&1 | Out-Null
                    if ($LASTEXITCODE -ne 0) {
                        $failed += $pkg
                        Write-Host "      Failed: $pkg" -ForegroundColor Red
                    }
                } catch {
                    $failed += $pkg
                    Write-Host "      Failed: $pkg" -ForegroundColor Red
                }
            }
        }
        
        if ($failed.Count -gt 0) {
            Write-Host "`n  Failed to install: $($failed -join ', ')" -ForegroundColor Red
            return $false
        }
        return $true
    } else {
        # No requirements.txt - install basic packages
        Write-Host "  Warning: requirements.txt not found. Installing basic packages..." -ForegroundColor Yellow
        $basicPackages = @('numpy', 'matplotlib', 'scipy')
        
        foreach ($pkg in $basicPackages) {
            Write-Host "    Installing $pkg..." -ForegroundColor Gray
            try {
                & $PythonExe -m pip install $pkg
            } catch {
                Write-Host "      Warning: Failed to install $pkg" -ForegroundColor Yellow
            }
        }
        return $true
    }
}

$success = Install-Packages -PythonExe $pythonExe -IsWindowsStore $python.IsWindowsStore

if ($success) {
    Write-Host "`nEnvironment setup complete!" -ForegroundColor Green
<<<<<<< HEAD
    Write-Host "Virtual environment created at: $venvPath" -ForegroundColor Cyan
    Write-Host "You can now run 'run_astm_noise.ps1' to start the application." -ForegroundColor Cyan
} else {
    Write-Host "`nSetup completed with errors!" -ForegroundColor Yellow
=======
    Write-Host "Virtual environment created at: $venvPath" -ForegroundColor Cyan
    Write-Host "You can now run 'run_astm_noise.ps1' to start the application." -ForegroundColor Cyan
} else {
    Write-Host "`nSetup completed with errors!" -ForegroundColor Yellow
=======
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
>>>>>>> 68e894c7f1ad82673a4945626a0c35375333bc91
>>>>>>> 206fc0808214fdd361282a3921544468223baef1
    Write-Host "Virtual environment created at: $venvPath" -ForegroundColor Cyan
    Write-Host "You may need to manually install missing packages." -ForegroundColor Yellow
    if ($python.IsWindowsStore) {
        Write-Host "`nWindows Store Python Note:" -ForegroundColor Yellow
        Write-Host "  Consider installing Python from python.org for better compatibility." -ForegroundColor Cyan
    }
}

Write-Host "`nPress any key to continue..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
