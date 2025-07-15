# Package ASTM Noise Analysis Tool for Distribution
# This script creates a clean distribution package

param(
    [string]$Version = "3.1.0",
    [switch]$SkipTests
)

Write-Host "ASTM Noise Analysis Tool - Distribution Packager" -ForegroundColor Green
Write-Host "Creating distribution package v$Version..." -ForegroundColor Yellow
Write-Host ""

# Get current directory
$currentDir = Get-Location

# Create package directory
$packageName = "ASTM-Noise-Analysis-Tool-v$Version"
$packagePath = Join-Path $currentDir $packageName

# Remove existing package if it exists
if (Test-Path $packagePath) {
    Write-Host "Removing existing package directory..." -ForegroundColor Yellow
    Remove-Item $packagePath -Recurse -Force
}

# Create new package directory
Write-Host "Creating package directory: $packageName" -ForegroundColor Cyan
New-Item -ItemType Directory -Path $packagePath | Out-Null

# Define files to include in distribution
$filesToInclude = @(
    "ASTMnoise.py",
    "ASTMnoise_modular.py",
    "data_processor.py",
    "gui_components.py", 
    "gui_plots.py",
    "convexHull.py", 
    "config.py",
    "utils.py",
    "__init__.py",
    "requirements.txt",
    "setup_env.bat",
    "setup_env.ps1", 
    "run_astm_noise.bat",
    "run_astm_noise.ps1",
    "INSTALL.bat",
    "README.md",
    "HELP.md",
    "DISTRIBUTION.md",
    "CHANGELOG.md",
    "PACKAGE_CHECKLIST.md"
)

# Copy files to package directory
Write-Host "Copying files to package..." -ForegroundColor Cyan
$copiedCount = 0
$missingFiles = @()

foreach ($file in $filesToInclude) {
    if (Test-Path $file) {
        Copy-Item $file $packagePath -Force
        Write-Host "  Success: $file" -ForegroundColor Green
        $copiedCount++
    } else {
        Write-Host "  Missing: $file" -ForegroundColor Red
        $missingFiles += $file
    }
}

Write-Host ""
Write-Host "Files copied: $copiedCount / $($filesToInclude.Count)" -ForegroundColor $(if ($copiedCount -eq $filesToInclude.Count) { "Green" } else { "Yellow" })

if ($missingFiles.Count -gt 0) {
    Write-Host "Missing files:" -ForegroundColor Red
    foreach ($file in $missingFiles) {
        Write-Host "  - $file" -ForegroundColor Red
    }
    Write-Host ""
}

# Clean up any development files that might have been copied
Write-Host "Cleaning development files..." -ForegroundColor Cyan
$cleanupPatterns = @("__pycache__", "*.pyc", "*.log", ".git*")

foreach ($pattern in $cleanupPatterns) {
    $itemsToRemove = Get-ChildItem -Path $packagePath -Name $pattern -Force -ErrorAction SilentlyContinue
    foreach ($item in $itemsToRemove) {
        $itemPath = Join-Path $packagePath $item
        Remove-Item $itemPath -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  Removed: $item" -ForegroundColor Green
    }
}

# Verify package contents
Write-Host ""
Write-Host "Package contents:" -ForegroundColor Cyan
$packageFiles = Get-ChildItem -Path $packagePath | Sort-Object Name
foreach ($file in $packageFiles) {
    $size = if ($file.PSIsContainer) { "(folder)" } else { "($([math]::Round($file.Length/1KB, 1)) KB)" }
    Write-Host "  $($file.Name) $size" -ForegroundColor Gray
}

# Calculate package size
$totalSize = (Get-ChildItem -Path $packagePath -Recurse | Measure-Object -Property Length -Sum).Sum
$totalSizeMB = [math]::Round($totalSize / 1MB, 2)
Write-Host ""
Write-Host "Total package size: $totalSizeMB MB" -ForegroundColor Yellow

# Test basic functionality if not skipped
if (-not $SkipTests) {
    Write-Host ""
    Write-Host "Running basic validation tests..." -ForegroundColor Cyan
    
    # Test that main file can be imported
    $testScript = @"
import sys
sys.path.insert(0, r'$packagePath')
try:
    import ASTMnoise
    import convexHull
    print('Success: Import test passed')
except Exception as e:
    print(f'Error: Import test failed: {e}')
    sys.exit(1)
"@
    
    $testFile = Join-Path $env:TEMP "astm_test.py"
    $testScript | Out-File -FilePath $testFile -Encoding UTF8
    
    try {
        $result = python $testFile 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Success: Python import test passed" -ForegroundColor Green
        } else {
            Write-Host "  Error: Python import test failed: $result" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ! Python test skipped (Python not available)" -ForegroundColor Yellow
    } finally {
        Remove-Item $testFile -ErrorAction SilentlyContinue
    }
    
    # Test that required files exist
    $requiredFiles = @("ASTMnoise.py", "requirements.txt", "README.md")
    foreach ($file in $requiredFiles) {
        if (Test-Path (Join-Path $packagePath $file)) {
            Write-Host "  Success: Required file: $file" -ForegroundColor Green
        } else {
            Write-Host "  Error: Missing required file: $file" -ForegroundColor Red
        }
    }
}

# Create ZIP archive
Write-Host ""
Write-Host "Creating ZIP archive..." -ForegroundColor Cyan
$zipPath = "$packageName.zip"

if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
    Write-Host "  Removed existing ZIP file" -ForegroundColor Yellow
}

try {
    Compress-Archive -Path $packagePath -DestinationPath $zipPath -Force
    $zipSize = [math]::Round((Get-Item $zipPath).Length / 1MB, 2)
    Write-Host "  Success: Created $zipPath ($zipSize MB)" -ForegroundColor Green
} catch {
    Write-Host "  Error: Failed to create ZIP: $_" -ForegroundColor Red
}

# Final summary
Write-Host ""
Write-Host "Distribution Package Complete!" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host "Package folder: $packageName" -ForegroundColor White
Write-Host "ZIP archive: $zipPath" -ForegroundColor White
Write-Host "Files included: $copiedCount" -ForegroundColor White
Write-Host "Package size: $totalSizeMB MB" -ForegroundColor White

if ($missingFiles.Count -eq 0) {
    Write-Host "Status: Ready for distribution [OK]" -ForegroundColor Green
} else {
    Write-Host "Status: Missing files - review before distribution [WARNING]" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Test the package on a clean machine" -ForegroundColor White
Write-Host "2. Extract $zipPath" -ForegroundColor White
Write-Host "3. Run INSTALL.bat or setup_env.ps1" -ForegroundColor White
Write-Host "4. Test the application functionality" -ForegroundColor White
Write-Host "5. Distribute the ZIP file to users" -ForegroundColor White
