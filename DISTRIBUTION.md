# ASTM Noise Analysis Tool - Distribution Package

This package contains everything you need to run the ASTM Noise Analysis Tool on Windows and macOS/Linux.

## Quick Start

1. **Extract** this entire folder to your desired location
2. **Run setup**:
  - Windows: Double-click `setup_env.bat` or run `\.\setup_env.ps1` in PowerShell
  - macOS/Linux: Run `./INSTALL.sh` (or `./setup_env.sh`)
3. **Start analysis**:
  - Windows: Double-click `run_astm_noise.bat` or run `\.\run_astm_noise.ps1` in PowerShell
  - macOS/Linux: Run `./run_astm_noise.sh`

## Package Contents

### Core Files
- `ASTMnoise.py` - Main application with GUI interface
- `convexHull.py` - Convex hull calculation utilities
- `config.py` - Application configuration and constants
- `__init__.py` - Package initialization

### Setup and Launch Scripts
- `setup_env.bat` / `setup_env.ps1` - Environment setup (run once)
- `run_astm_noise.bat` / `run_astm_noise.ps1` - Application launcher
- `INSTALL.sh` / `setup_env.sh` - Environment setup (macOS/Linux)
- `run_astm_noise.sh` - Application launcher (macOS/Linux)

### Documentation
- `README.md` - Comprehensive user guide and setup instructions
- `HELP.md` - Detailed usage guide with examples
- `DISTRIBUTION.md` - This file (distribution information)
- `CHANGELOG.md` - Version history and updates

### Dependencies
- `requirements.txt` - Python package dependencies

## System Requirements

- **Operating System**: Windows 7 or later
- **Python**: 3.8 or later (from python.org or Microsoft Store)
- **Memory**: 4GB RAM minimum (8GB recommended for large datasets)
- **Storage**: 100MB free space (plus space for your data files)

## Installation Notes

- The setup script creates a virtual environment in `%USERPROFILE%\Documents\Python Environments\astm-noise-analysis`
- This keeps the tool's dependencies separate from any existing Python installations
- No administrator privileges required
- The tool can be run from any location after setup
- macOS/Linux setup creates a local `./.venv` in the extracted folder
- **Wheel-only installs**: setup scripts enforce prebuilt wheels only (no compiling from source)
- **Compatible with both**:
  - Standard Python installations from python.org
  - Microsoft Store Python installations
- The setup script automatically detects your Python installation type and uses the appropriate installation method

## Sharing This Package

To share with colleagues:
1. Zip the entire folder containing all these files
2. Recipients should extract and run the setup script
3. No additional configuration needed

## Support

For technical support or questions about this tool, contact [Your Contact Information].

## Version Information

**Current Version**: 3.2.0
**Last Updated**: January 2026
**Compatible with**: Python 3.12/3.13 on Windows, macOS, and Linux (requires wheels-only dependencies)
