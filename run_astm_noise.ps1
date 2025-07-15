# Launcher for ASTM Noise Analysis Tool

param(
    [switch]$ShowCompleteDataset,
    [switch]$Show,  # Short alias for ShowCompleteDataset
    [switch]$ShowHighNoiseIntervals,
    [switch]$Intervals,  # Short alias for ShowHighNoiseIntervals
    [int]$NIntervals = 0,  # Number of intervals to show
    [double]$NoiseThreshold = $null,  # Threshold value for noise intervals
    [switch]$Help,
    [switch]$h      # Short alias for Help
)

# Show help if requested
if ($Help -or $h) {
    if (Test-Path "HELP.md") {
        Get-Content "HELP.md" | Write-Host
    } else {
        Write-Host "ASTM Noise Analysis Tool - Help" -ForegroundColor Green
        Write-Host ""
        Write-Host "Usage:" -ForegroundColor Yellow
        Write-Host "  .\run_astm_noise.ps1                            - Standard analysis (ASTM interval only)"
        Write-Host "  .\run_astm_noise.ps1 -ShowCompleteDataset       - Analysis with both plots"
        Write-Host "  .\run_astm_noise.ps1 -Show                      - Same as above (short form)"
        Write-Host "  .\run_astm_noise.ps1 -ShowHighNoiseIntervals    - Show high noise intervals"
        Write-Host "  .\run_astm_noise.ps1 -Intervals -NIntervals 10  - Show top 10 noise intervals"
        Write-Host "  .\run_astm_noise.ps1 -Intervals -NoiseThreshold 1200  - Show all intervals above 1200"
        Write-Host "  .\run_astm_noise.ps1 -Help                      - Show this help"
        Write-Host ""
        Write-Host "Options:" -ForegroundColor Yellow
        Write-Host "  -ShowCompleteDataset, -Show      Display both ASTM interval and complete dataset plots"
        Write-Host "  -ShowHighNoiseIntervals, -Intervals  Identify and highlight highest noise intervals"
        Write-Host "  -NIntervals <number>             Number of high noise intervals to display (default: 0)"
        Write-Host "  -NoiseThreshold <value>          Show all intervals above this threshold (alternative to -NIntervals)"
        Write-Host "  -Help, -h                        Show help information"
        Write-Host ""
        Write-Host "For detailed documentation, see HELP.md" -ForegroundColor Cyan
    }
    return
}

# Handle the short aliases
if ($Show) {
    $ShowCompleteDataset = $true
}
if ($Intervals) {
    $ShowHighNoiseIntervals = $true
}

Write-Host "Starting ASTM Noise Analysis Tool..." -ForegroundColor Green

# Display mode information
$modeInfo = @()
if ($ShowCompleteDataset) {
    $modeInfo += "Complete dataset plots"
}
if ($ShowHighNoiseIntervals) {
    if ($NoiseThreshold -ne $null) {
        $modeInfo += "High noise intervals (above threshold $NoiseThreshold)"
    } elseif ($NIntervals -gt 0) {
        $modeInfo += "High noise intervals (top $NIntervals)"
    } else {
        $modeInfo += "High noise intervals (no specific criteria)"
    }
}

if ($modeInfo.Count -eq 0) {
    Write-Host "Mode: Standard analysis (ASTM interval only)" -ForegroundColor Cyan
} else {
    Write-Host "Mode: $($modeInfo -join ', ')" -ForegroundColor Cyan
}

# Change to script directory
Set-Location -Path $PSScriptRoot

# Try to use the virtual environment if it exists
$localVenv = ".venv\Scripts\python.exe"
$centralVenvDir = Join-Path $env:USERPROFILE "Documents\Python Environments"
$projectName = "astm-noise-analysis"
$centralVenv = Join-Path $centralVenvDir "$projectName\Scripts\python.exe"

# Build command arguments
$arguments = @("ASTMnoise.py")
if ($ShowCompleteDataset) {
    $arguments += "--show-complete-dataset"
}
if ($ShowHighNoiseIntervals) {
    $arguments += "--show-high-noise-intervals"
    if ($NoiseThreshold -ne $null) {
        $arguments += "--noise-threshold"
        $arguments += $NoiseThreshold.ToString()
    } else {
        $arguments += "--n-intervals"
        $arguments += $NIntervals.ToString()
    }
}

if (Test-Path $centralVenv) {
    Write-Host "Using centralized virtual environment..." -ForegroundColor Green
    Write-Host "Python executable: $centralVenv" -ForegroundColor Gray
    & $centralVenv @arguments
} elseif (Test-Path $localVenv) {
    Write-Host "Using local virtual environment..." -ForegroundColor Green
    Write-Host "Python executable: $(Resolve-Path $localVenv)" -ForegroundColor Gray
    & $localVenv @arguments
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    Write-Host "Using Python launcher (py)..." -ForegroundColor Yellow
    & py @arguments
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "Using system Python..." -ForegroundColor Yellow
    & python @arguments
} else {
    Write-Host "Error: No Python executable found!" -ForegroundColor Red
    Write-Host "Please ensure Python is installed and accessible." -ForegroundColor Red
    Write-Host "Or run 'setup_env.ps1' to create a virtual environment." -ForegroundColor Yellow
}

# Pause equivalent
Write-Host "`nPress any key to continue..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
