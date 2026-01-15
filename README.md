# ASTM Noise Analysis Tool

**Version 3.1.1** - A Python-based tool for analyzing noise in lamp data according to ASTM standards. This application provides a modern GUI interface with separate plot windows for analyzing noise statistics and visualizing complete datasets.

## Features

- **Multi-file Processing**: Load and process multiple tab-delimited data files
- **Automated Noise Calculation**: Calculates noise using convex hull analysis
- **Statistical Analysis**: Computes mean and maximum noise values for both main and reference channels
- **Dual Plot Visualization**: 
  - ASTM Noise Interval plot (minutes) with 60-minute compliance line
  - Optional Complete Dataset plot (hours) with total time display
- **High Noise Interval Analysis**: Identify and analyze problematic time periods
  - **Configurable Plot Limits**: Control number of detailed interval plots (default: 8)
  - **Interactive Configuration**: Adjust plot limits directly in analysis window
- **Separate Windows**: Each plot opens in its own dedicated window for better workflow
- **Smart Export**: Automatic filename generation
- **Command Line Options**: PowerShell integration with advanced parameter support

## System Requirements

**Python Version**: This package requires **Python 3.12 or Python 3.13**. Python 3.14 is not yet supported as pre-built wheels for core numerical libraries (NumPy, SciPy, matplotlib) are not yet available for this version.

## Setup on a New Computer

### Download and Extract Files

1. **Download the Project**:
   - Download the ZIP file containing all project files
   - Choose a good location on your computer (e.g., `C:\Tools\ASTM-Noise-Analysis` or `C:\Users\[username]\Documents\ASTM-Noise-Analysis`)
   - Right-click the ZIP file and select "Extract All..."
   - Navigate to the extracted folder in File Explorer

2. **Open Command Prompt/PowerShell**:
   - In the extracted folder, hold Shift and right-click in an empty area
   - Select "Open PowerShell window here" or "Open command window here"
   - This ensures you're in the correct directory for the setup scripts

### Environment Setup

3. **Install Python** (if not already installed):
   
   **Option A - Python.org (Recommended):**
   - Download Python 3.12 or 3.13 from https://www.python.org/downloads/
   - Make sure to check "Add Python to PATH" during installation
   - Verify installation: `py --version`
   
   **Option B - Microsoft Store:**
   - Open Microsoft Store and search for "Python 3.12" or "Python 3.13"
   - Install and the setup script will automatically detect it
   
   **Note**: The setup script automatically detects and works with both Python.org and Microsoft Store installations.

4. **Set up the environment**:
   
   **Option A - PowerShell (Recommended):**
   ```powershell
   .\setup_env.ps1
   ```
   
   **Option B - Batch/Command Prompt:**
   ```batch
   setup_env.bat
   ```
   
   This will:
   - Create a new virtual environment in `%USERPROFILE%\Documents\Python Environments\astm-noise-analysis`
   - Install all required packages from `requirements.txt`

5. **Run the application**:
   
   **Option A - PowerShell (Recommended):**
   ```powershell
   .\run_astm_noise.ps1
   ```
   
   **Option B - Batch/Command Prompt:**
   ```batch
   run_astm_noise.bat
   ```

## Command Line Usage

### Basic Usage (ASTM plot only - faster):
```bash
python ASTMnoise.py
```

### With Complete Dataset (both plots):
```bash
python ASTMnoise.py --show-complete-dataset
```

### Help:
```bash
python ASTMnoise.py --help
```

## Files in this Project

- `ASTMnoise.py` - Main GUI application with dual plot functionality
- `convexHull.py` - Convex hull calculation module for noise determination
- `run_astm_noise.ps1` - PowerShell launcher script
- `run_astm_noise.bat` - Batch launcher script
- `setup_env.ps1` - Environment setup script (PowerShell)
- `setup_env.bat` - Environment setup script (Batch)
- `requirements.txt` - Python package dependencies
- `README.md` - This documentation file

## Usage Workflow

1. **Launch the Application**: Run the launcher script or use command line
2. **File Selection**: The application will prompt you to select tab-delimited text files (.txt)
3. **Data Processing**: The tool will:
   - Load data from each file (skipping 2-row headers)
   - Extract main channel (column 3) and reference channel (column 5) data
   - Calculate noise values using convex hull analysis on data subsets
   - Continue prompting for files until 120 noise values are collected for each channel
4. **Plot Windows Open**:
   - **ASTM Noise Interval Plot**: Shows selected data in minutes with 60-minute compliance line
   - **Complete Dataset Plot** (optional): Shows all files combined in hours with reference lines
5. **Export Results**:
   - CSV file with noise statistics saved automatically
   - Click "Export" buttons to save plots as PNG with automatic filename generation
   - Green success messages confirm successful exports

## Plot Features

### ASTM Noise Interval Plot
- **Time Scale**: Minutes (0-60+ minutes)
- **Title**: Shows parent folder name + "ASTM Noise"
- **Reference Line**: Red dashed line at 60 minutes (ASTM compliance limit)
- **Export**: `[folder] noise containing the time [timestamp].png`

### Complete Dataset Plot
- **Time Scale**: Hours (total dataset duration)
- **Title**: Shows total time in hours (e.g., "Complete Dataset - 4.2 hours total time")
- **Reference Lines**: 
  - Green dashed line: End of first file (start of second dataset)
  - Red dashed line: 60 minutes after green line (ASTM limit)
- **Export**: `[folder] complete dataset [X.X] hours.png`

## Data Format Requirements

The application expects tab-delimited text files with:
- **Header**: 2 rows (automatically skipped)
- **Filename Pattern**: `YYYY-MM-DD_HH-mm-ss_DataCollection.txt`
- **Columns**:
  - Column 1: Time values (seconds)
  - Column 3: Main channel intensity data
  - Column 5: Reference channel intensity data

## Algorithm Details

- **Subset Size**: Automatically calculated based on time intervals (typically 30-second windows)
- **Noise Calculation**: Uses convex hull analysis to determine maximum noise in each subset
- **Data Collection**: Continues until 120 noise values are collected for each channel
- **Time Handling**: 
  - Original timestamps used for noise calculations
  - Time offsets applied for continuous visualization across files
- **File Processing**: Files sorted by timestamp for chronological order

## Dependencies

- **numpy**: Numerical computing and data manipulation
- **matplotlib**: Data visualization and plotting
- **scipy**: Scientific computing (convex hull calculations)
- **tkinter**: GUI framework (included with Python)
- **argparse**: Command line argument parsing (included with Python)

## Output Files

- **noise_analysis_results_python.csv**: Statistical results (mean/max noise for both channels)
- **ASTM Plot**: `[folder] noise containing the time [timestamp].png`
- **Complete Dataset**: `[folder] complete dataset [X.X] hours.png`

## Advanced Features

- **Portable Environment**: Virtual environment 
- **Error Handling**: Silent error handling for corrupted or missing files
- **Memory Efficient**: Processes large datasets without memory issues
- **Cross-Platform**: Works on Windows with both PowerShell and Command Prompt
- **Professional Output**: High-resolution plots suitable for reports and presentations

## Troubleshooting

- **PowerShell execution policy errors**: Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- **Batch file issues**: Try running the .bat files from Command Prompt instead of PowerShell
- **Python not found**: Make sure Python is installed and added to PATH
  - The setup script will automatically try `py`, `python3`, and `python` commands
  - Works with both python.org and Microsoft Store installations
- **Windows Store Python issues**: If you encounter problems, consider installing Python from python.org instead
- **Virtual environments**: Stored in `%USERPROFILE%\Documents\Python Environments\`
- **GUI doesn't appear**: Check that tkinter is properly installed with your Python distribution
- **Import errors**: Run `setup_env.ps1` to ensure all dependencies are installed
- **Plot windows not appearing**: Check if windows are opening behind other applications

## Technical Notes

- **Dual Window Architecture**: Each plot type opens in its own optimized window
- **Time Conversion**: Automatic conversion between seconds (data) and minutes/hours (display)
- **Smart File Detection**: Automatically finds and processes all matching files in folder
- **Robust Processing**: Handles incomplete subsets and file errors gracefully
- **Export Feedback**: Visual confirmation of successful file exports
- **Argument Parsing**: Professional command-line interface with help documentation
