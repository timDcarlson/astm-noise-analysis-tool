# ASTM Noise Analysis Tool

A Python-based tool for analyzing noise in lamp data according to ASTM standards. This application provides a GUI interface for loading tab-delimited data files, calculating noise statistics, and visualizing the results.

## Features

- **Multi-file Processing**: Load and process multiple tab-delimited data files
- **Automated Noise Calculation**: Calculates noise using convex hull analysis
- **Statistical Analysis**: Computes mean and maximum noise values for both main and reference channels
- **Data Visualization**: Generates scatter plots of raw data with noise statistics
- **Export Functionality**: Saves results to CSV and exports plots as PNG images
- **Progress Tracking**: Real-time feedback on data collection progress

## Setup on a New Computer

1. **Install Python** (if not already installed):
   - Download from https://www.python.org/downloads/
   - Make sure to check "Add Python to PATH" during installation
   - Verify installation: `py --version`

2. **Set up the environment**:
   
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

3. **Run the application**:
   
   **Option A - PowerShell (Recommended):**
   ```powershell
   .\run_astm_noise.ps1
   ```
   
   **Option B - Batch/Command Prompt:**
   ```batch
   run_astm_noise.bat
   ```

## Files in this Project

- `run_astm_noise.ps1` - Main launcher script for the application (PowerShell)
- `run_astm_noise.bat` - Main launcher script for the application (Batch)
- `setup_env.ps1` - Environment setup script for new computers (PowerShell)
- `setup_env.bat` - Environment setup script for new computers (Batch)
- `requirements.txt` - List of Python package dependencies
- `ASTMnoise.py` - Main GUI application for noise analysis
- `convexHull.py` - Convex hull calculation module for noise determination
- `README.md` - This documentation file

## Usage

1. **Launch the Application**: Run `run_astm_noise.ps1` (PowerShell) or `run_astm_noise.bat` (Command Prompt)
2. **Select Data Files**: The application will prompt you to select tab-delimited text files (.txt)
3. **Data Processing**: The tool will:
   - Load data from each file (skipping 2-row headers)
   - Extract main channel (column 3) and reference channel (column 5) data
   - Calculate noise values using convex hull analysis on data subsets
   - Continue prompting for files until 120 noise values are collected for each channel
4. **View Results**: 
   - Statistical summary (mean and max noise) for both channels
   - Scatter plot visualization of all raw data
   - Legend showing noise statistics
5. **Export Results**:
   - CSV file with noise statistics saved automatically
   - Use "Export Plot" button to save the visualization as PNG

## Data Format Requirements

The application expects tab-delimited text files with:
- **Header**: 2 rows (automatically skipped)
- **Columns**:
  - Column 1: Time values
  - Column 3: Main channel intensity data
  - Column 5: Reference channel intensity data

## Algorithm Details

- **Subset Size**: Automatically calculated based on time intervals (typically 30-second windows)
- **Noise Calculation**: Uses convex hull analysis to determine maximum noise in each subset
- **Data Collection**: Continues until 120 noise values are collected for each channel
- **Visualization**: Combines data from all files with time offsets for continuous display

## Manual Setup (Alternative)

If you prefer to set up manually:

```batch
REM Create virtual environment in centralized location
set VENV_PATH=%USERPROFILE%\Documents\Python Environments\astm-noise-analysis
py -m venv "%VENV_PATH%"

REM Install packages
"%VENV_PATH%\Scripts\python.exe" -m pip install --upgrade pip
"%VENV_PATH%\Scripts\python.exe" -m pip install -r requirements.txt

REM Run the application
run_astm_noise.bat
```

## Dependencies

- **numpy**: Numerical computing and data manipulation
- **matplotlib**: Data visualization and plotting
- **scipy**: Scientific computing (convex hull calculations)
- **tkinter**: GUI framework (included with Python)

## Output Files

- **noise_analysis_results_python.csv**: Statistical results (mean/max noise for both channels)
- **[folder_name] noise containing the time [filename].png**: Scatter plot visualization

## Troubleshooting

- **PowerShell execution policy errors**: Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- **Batch file issues**: Try running the .bat files from Command Prompt instead of PowerShell
- **Python not found**: Make sure Python is installed and added to PATH
- **Virtual environments**: Stored in `%USERPROFILE%\Documents\Python Environments\`
- **OneDrive conflicts**: The environments are created outside OneDrive to avoid syncing conflicts
- **GUI doesn't appear**: Check that tkinter is properly installed with your Python distribution
- **Import errors**: Run `setup_env.ps1` to ensure all dependencies are installed

## Technical Notes

- The tool processes data in chunks to handle large datasets efficiently
- Time offsets are applied for visualization while preserving original timestamps for calculations
- Incomplete subsets at file ends are automatically excluded from noise calculations
- The convex hull method provides robust noise estimation even with irregular data patterns
